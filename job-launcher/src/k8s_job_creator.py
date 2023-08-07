import csv
import time
import json
from braingeneers.iot.messaging import MessageBroker
from kubernetes import client, config
from braingeneers.utils.smart_open_braingeneers import open
from threading import Event, Thread
import functools
import traceback

LOGS_PATH = 's3://braingeneers/services/mqtt_job_listener/logs'
MQTT_ERROR_TOPIC = 'services/mqtt_job_listener/ERROR'


class K8sJobCreator:
    def __init__(self, job_info, namespace='braingeneers', message_broker=None):
        config.load_kube_config()
        self.job_info = job_info
        self.namespace = namespace
        self.api_instance = client.BatchV1Api()
        self.mb = message_broker

    def create_job_object(self):
        # Configure/create Pod template container
        container = client.V1Container(
            name=self.job_info['job_name'],
            image=self.job_info['image'],
            resources=client.V1ResourceRequirements(
                requests={
                    "cpu": self.job_info['cpu_request'],
                    "memory": self.job_info['memory_request'],
                    "nvidia.com/gpu": self.job_info['gpu'],
                    "ephemeral-storage": self.job_info['disk_request'],
                },
                limits={
                    "cpu": self.job_info['cpu_limit'],
                    "memory": self.job_info['memory_limit'],
                    "nvidia.com/gpu": self.job_info['gpu'],
                    "ephemeral-storage": self.job_info['disk_limit'],
                }
            ),
            env=[client.V1EnvVar(name="JOB_NAME", value=self.job_info['job_name'])]  # Set JOB_NAME environment variable
        )

        # Create and configure a spec section
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": self.job_info['job_name']}),
            spec=client.V1PodSpec(restart_policy="Never", containers=[container]))

        # Create the specification of deployment
        spec = client.V1JobSpec(
            template=template,
            backoff_limit=0,
            parallelism=int(self.job_info['parallelism']))  # Add parallelism to the job spec

        # Instantiate the job object
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=self.job_info['job_name']),
            spec=spec)

        return job

    def create_and_start_job(self):
        try:
            job = self.create_job_object()
            self.api_instance.create_namespaced_job(namespace=self.namespace, body=job)
            print(f'Job {self.job_info["job_name"]} created\n')
        except Exception as e:
            send_error_message(self.mb, 'Error when creating and starting job', e)

    def is_job_completed(self, job_name):
        try:
            api_response = self.api_instance.read_namespaced_job_status(job_name, self.namespace)
            return api_response.status.succeeded is not None
        except Exception as e:
            send_error_message(self.mb, 'Error when checking job completion status:', e)

    def get_job_status(self, job_name):
        try:
            api_response = self.api_instance.read_namespaced_job_status(job_name, self.namespace)
            if api_response.status.succeeded is not None and api_response.status.succeeded == 1:
                return 'succeeded'
            elif api_response.status.failed is not None and api_response.status.failed > 0:
                return 'failed'
            else:
                return 'running'
        except Exception as e:
            send_error_message(self.mb, 'Error when getting job status', e)

    def handle_completed_job(self, job_name):
        try:
            logs = self.get_job_logs(job_name)
            status = self.get_job_status(job_name)
            self.copy_logs_to_s3(logs, job_name)
            print(f'Job {job_name} completed, logs saved to {LOGS_PATH}/{job_name}.txt\n')

            if status == 'failed':
                send_error_message(self.mb, f'Job {job_name} failed. Logs at {LOGS_PATH}/{job_name}.txt', None)
            else:
                self.send_completion_message(job_name, status)

            self.delete_job(job_name)
        except Exception as e:
            send_error_message(self.mb, 'Error when handling completed job', e)

    def get_job_logs(self, job_name):
        try:
            core_v1_api = client.CoreV1Api()
            pod_list = core_v1_api.list_namespaced_pod(self.namespace, label_selector=f"app={job_name}")
            if not pod_list.items:
                print(f'No pods found for job: {job_name}\n')
                return ''
            pod_name = pod_list.items[0].metadata.name
            return core_v1_api.read_namespaced_pod_log(name=pod_name, namespace=self.namespace)
        except Exception as e:
            send_error_message(self.mb, f'Error when getting job logs', e)

    def delete_job(self, job_name):
        try:
            delete_options = client.V1DeleteOptions(propagation_policy="Foreground")
            self.api_instance.delete_namespaced_job(job_name, self.namespace, body=delete_options)
            print(f'Job {job_name} deleted\n')
        except Exception as e:
            send_error_message(self.mb, f'Error when deleting job', e)

    def copy_logs_to_s3(self, logs, job_name):
        try:
            with open(f'{LOGS_PATH}/{job_name}.txt', 'w') as f:
                f.write(logs)
        except Exception as e:
            send_error_message(self.mb, f'Error when copying logs to S3', e)

    def send_completion_message(self, job_name, status):
        try:
            mqtt_topic = f'services/mqtt_job_listener/job_complete/{job_name}'
            self.mb.publish_message(topic=mqtt_topic, message={'status': status})
            print(f'Job {job_name} published job_complete message to {mqtt_topic} with status {status}\n')
        except Exception as e:
            send_error_message(self.mb, f'Error when sending completion message', e)


class MQTTJobListener:
    def __init__(self, csv_file, namespace='braingeneers'):
        config.load_kube_config()
        self.namespace = namespace
        self.csv_file = csv_file
        self.mb = MessageBroker()

        print('Starting listener for REFRESH events.\n')
        self.mb.subscribe_message("services/mqtt_job_listener/REFRESH", self.refresh_jobs)

    def refresh_jobs(self, _topic, _message):
        print('REFRESH event received, refreshing jobs.\n')
        try:
            self.start_mqtt_listeners()
        except Exception as e:
            send_error_message(self.mb, f'Error when refreshing jobs', e)

    def start_mqtt_listeners(self):
        try:
            print(f'Reading jobs from {self.csv_file}\n')
            with open(self.csv_file, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    job_info = dict(row).copy()
                    mqtt_topic = job_info["mqtt_topic"]  # Extracts MQTT topic from the CSV file.
                    print(f'Subscribing to {mqtt_topic} with parameters {job_info}\n')
                    self.mb.subscribe_message(
                        mqtt_topic,
                        functools.partial(self.handle_job_request, job_info=job_info)
                    )
        except Exception as e:
            send_error_message(self.mb, f'Error when starting MQTT listeners', e)

    def handle_job_request(self, topic, message, job_info):
        try:
            print(f'Handling job request on topic {topic} {message} {job_info}\n')
            job_info.update(message)  # combine job info from the csv file and the mqtt message
            job_creator = K8sJobCreator(job_info, self.namespace, self.mb)
            job_creator.create_and_start_job()

            # Create a new thread for monitoring the job completion to handle it asynchronously
            monitor_thread = Thread(target=self.monitor_job, args=(job_creator, job_info,))
            monitor_thread.start()

        except Exception as e:
            send_error_message(self.mb, 'Error when handling job request', e)

    def monitor_job(self, job_creator, job_info):
        """Function to monitor the status of a job."""
        try:
            while True:
                status = job_creator.get_job_status(job_info['job_name'])
                if status in ['succeeded', 'failed']:
                    break
                time.sleep(5)

            if status == 'failed':
                self.check_container_error(job_info['job_name'], job_creator)

            job_creator.handle_completed_job(job_info['job_name'])
        except Exception as e:
            send_error_message(self.mb, 'Error when monitoring job', e)

    def check_container_error(self, job_name, job_creator):
        """Function to check for CreateContainerError and report to MQTT."""
        try:
            core_v1_api = client.CoreV1Api()
            pod_list = core_v1_api.list_namespaced_pod(job_creator.namespace, label_selector=f"app={job_name}")
            if pod_list.items:
                pod = pod_list.items[0]
                for container_status in pod.status.container_statuses:
                    if container_status.state.waiting and container_status.state.waiting.reason == "CreateContainerError":
                        send_error_message(self.mb, 'CreateContainerError', Exception(container_status.state.waiting.message))
                        break
        except Exception as e:
            send_error_message(self.mb, 'Error when checking for CreateContainerError', e)


def send_error_message(mb: MessageBroker, message_prefix: str, e: Exception):
    error_message = message_prefix if e is None else f'{message_prefix}: {str(e)}'
    mb.publish_message(topic=MQTT_ERROR_TOPIC, message={'error': error_message})
    print(f'Error with tracback: {message_prefix}')
    print(traceback.format_exc())


if __name__ == "__main__":
    print('Starting MQTTJobListener\n')
    job_listener = MQTTJobListener("s3://braingeneers/services/mqtt_job_listener/jobs.csv")
    job_listener.start_mqtt_listeners()
    Event().wait()
