// Define other variables that should be passed to the script, if the workflow is triggered by MQTT these
// variables must be available in the MQTT payload as a JSON dictionary with the variable name. For example
// for params.UUID the MQTT payload should include at a minimum {"UUID": "2020-01-01-e-demo"}
// params.UUID = 'not-set'
params.xyz = 'notset'

workflow {
    data = pim(params.xyz)
    pom(params.xyz, data)
    pom.out.view()
}

process pim {
    container 'ubuntu:22.04'
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

process pom {
    container 'ubuntu:22.04'
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
        echo "Running POM! UUID: ${xyz} AND " &> n.txt
        cat ${data} >> n.txt
        """
}
