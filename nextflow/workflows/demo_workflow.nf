// If you want the workflow to be triggered by an MQTT message you must define the MQTT_TOPIC_TRIGGER variable
MQTT_TOPIC_TRIGGER = 'experiments/upload'

// Define other variables that should be passed to the script, if the workflow is triggered by MQTT these
// variables must be available in the MQTT payload as a JSON dictionary with the variable name. For example
// for params.UUID the MQTT payload should include at a minimum {"UUID": "2020-01-01-e-demo"}
// params.UUID = 'not-set'
params.xyz = 'notset'

workflow {
    data = helloWorld1(params.xyz)
//     helloWorld2(params.xyz, data)
}

process helloWorld1 {
    container 'ubuntu:latest'

    // Define the resource requirements
    cpus 1
    memory '1 GB'
    disk '1 GB'

    input:
    val xyz

    output:
    file 'output.txt'

    pod: '''
    apiVersion: v1
    kind: Pod
    spec:
      containers:
      - name: main
        securityContext:
          runAsUser: 0
          privileged: false
    '''

//     pod = '''
//     apiVersion: v1
//     kind: Pod
//     spec:
//       containers:
//       - name: main
//         securityContext:
//           runAsUser: 1000
//           privileged: false
//     '''

    pod = [
        """
        apiVersion: v1
        kind: Pod
        spec:
          containers:
          - name: main
            securityContext:
              runAsUser: 1000
              privileged: false
        """
    ]

//     pod = [
//         'spec': [
//             'containers': [
//                 [
//                     'name': 'main',
//                     'securityContext': [
//                         'privileged': false
//                     ]
//                 ]
//             ]
//         ]
//     ]

//     pod = [
//       securityContext: {
//         privileged = false
//       }
//     ]

//     pod = [
//       {
//         'containers': [{
//           'securityContext': {
//             'privileged': false,
//             }
//           }
//         ]
//       }
//     ]

//     '''
//     apiVersion: v1
//     kind: Pod
//     spec:
//       securityContext:
//         runAsUser: 0
//       containers:
//       - name: main
//         securityContext:
//           privileged: false
//     ''']

    """
    echo "Running Hello World Container 1! UUID: ${xyz}"
    """
}

// process helloWorld2 {
//     container 'ubuntu:latest'
//
//     // Define the resource requirements
//     cpus 1
//     memory '1 GB'
//     disk '1 GB'
//
//     input:
//     val xyz
//     file data
//
//     """
//     echo "Running Hello World Container 2! UUID: ${xyz}"
//     cat ${data}
//     """
// }