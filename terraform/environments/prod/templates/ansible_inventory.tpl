{
  "all": {
    "hosts": {
      "prod-collector-1": {
        "ansible_host": "${collector_1.ansible_host}",
        "ansible_user": "${collector_1.ansible_user}",
        "ansible_port": ${collector_1.ansible_port},
        "instance_id": "${collector_1.instance_id}",
        "service_type": "data-collector",
        "environment": "prod",
        "availability_zone": "a"
      },
      "prod-collector-2": {
        "ansible_host": "${collector_2.ansible_host}",
        "ansible_user": "${collector_2.ansible_user}",
        "ansible_port": ${collector_2.ansible_port},
        "instance_id": "${collector_2.instance_id}",
        "service_type": "data-collector",
        "environment": "prod",
        "availability_zone": "b"
      },
      "prod-exec-1": {
        "ansible_host": "${execution_1.ansible_host}",
        "ansible_user": "${execution_1.ansible_user}",
        "ansible_port": ${execution_1.ansible_port},
        "instance_id": "${execution_1.instance_id}",
        "service_type": "execution",
        "environment": "prod",
        "freqtrade_api_port": 8080
      },
      "prod-monitor": {
        "ansible_host": "${monitor.ansible_host}",
        "ansible_user": "${monitor.ansible_user}",
        "ansible_port": ${monitor.ansible_port},
        "instance_id": "${monitor.instance_id}",
        "service_type": "monitor",
        "environment": "prod",
        "prometheus_port": 9090,
        "grafana_port": 3000,
        "alertmanager_port": 9093
      }
    },
    "children": {
      "data_collectors": {
        "hosts": [
          "prod-collector-1",
          "prod-collector-2"
        ]
      },
      "execution_engines": {
        "hosts": [
          "prod-exec-1"
        ]
      },
      "monitors": {
        "hosts": [
          "prod-monitor"
        ]
      }
    },
    "vars": {
      "ansible_python_interpreter": "/usr/bin/python3",
      "ansible_become": true,
      "ansible_become_method": "sudo",
      "environment": "prod",
      "monitoring_retention_days": "30d",
      "log_level": "INFO"
    }
  }
}

