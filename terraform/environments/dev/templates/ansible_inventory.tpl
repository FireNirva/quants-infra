{
  "all": {
    "hosts": {
      "dev-collector-1": {
        "ansible_host": "${collector_1.ansible_host}",
        "ansible_user": "${collector_1.ansible_user}",
        "ansible_port": ${collector_1.ansible_port},
        "instance_id": "${collector_1.instance_id}",
        "service_type": "data-collector",
        "environment": "dev"
      },
      "dev-monitor": {
        "ansible_host": "${monitor.ansible_host}",
        "ansible_user": "${monitor.ansible_user}",
        "ansible_port": ${monitor.ansible_port},
        "instance_id": "${monitor.instance_id}",
        "service_type": "monitor",
        "environment": "dev",
        "prometheus_port": 9090,
        "grafana_port": 3000
      }
    },
    "children": {
      "data_collectors": {
        "hosts": [
          "dev-collector-1"
        ]
      },
      "monitors": {
        "hosts": [
          "dev-monitor"
        ]
      }
    },
    "vars": {
      "ansible_python_interpreter": "/usr/bin/python3",
      "ansible_become": true,
      "ansible_become_method": "sudo",
      "environment": "dev"
    }
  }
}

