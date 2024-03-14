// If you want the workflow to be triggered by an MQTT message you must define the MQTT_TOPIC_TRIGGER variable
MQTT_TOPIC_TRIGGER = 'experiments/upload'

// file('s3://braingeneers/').list().each{ println it }

// Define other variables that should be passed to the script, if the workflow is triggered by MQTT these
// variables must be available in the MQTT payload as a JSON dictionary with the variable name. For example
// for params.UUID the MQTT payload should include at a minimum {"UUID": "2020-01-01-e-demo"}
// params.UUID = 'not-set'
params.xyz = 'notset'

workflow {
    data = pim(params.xyz)
    pem(params.xyz, data)
    pem.out.view()
}

process pim {
    container 'quay.io/ucsc_cgl/mqtt-nextflow-s3:0.0'
    cpus '1'
    memory '100 MB'
    disk '100 MB'

    input:
        val xyz

    output:
        path 'o.txt'

    script:
        """
        echo "Running PIM! UUID: ${xyz}" &> o.txt
        """
}

process pem {
    container 'quay.io/ucsc_cgl/mqtt-nextflow-s3:0.0'
    cpus '1'
    memory '100 MB'
    disk '100 MB'

    input:
        val xyz
        path data

    output:
        path 'n.txt'

    script:
        """
        echo "Running PEM! UUID: ${xyz} AND " &> n.txt
        cat ${data} >> n.txt
        """
}
