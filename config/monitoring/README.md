# 监控配置目录

此目录包含从 `quants-lab/config/` 同步的监控配置文件。

## 配置来源

所有监控配置都来源于 `quants-lab` 项目，使用以下脚本同步：

```bash
infrastructure/scripts/sync_monitoring_configs.sh
```

## 目录结构

```
config/monitoring/
├── prometheus/
│   ├── alert_rules.yml              # 告警规则（从 quants-lab 复制）
│   └── prometheus.template.yml      # Prometheus 配置模板
├── alertmanager/
│   └── alertmanager.template.yml    # Alertmanager 配置模板
└── grafana/
    ├── provisioning/                # Grafana 自动配置
    │   ├── datasources/
    │   └── dashboards/
    └── dashboards/                  # Dashboard JSON 文件
```

## 更新配置

如果 quants-lab 中的监控配置有更新，运行以下命令同步：

```bash
# 复制最新配置
cd infrastructure
./scripts/sync_monitoring_configs.sh --copy --force

# 或使用软链接（开发环境推荐）
./scripts/sync_monitoring_configs.sh --symlink --force
```

## 配置使用

这些配置文件被 Ansible playbooks 使用：

- `ansible/playbooks/monitor/setup_prometheus.yml` - 使用 alert_rules.yml
- `ansible/playbooks/monitor/setup_alertmanager.yml` - 使用 alertmanager 配置
- `ansible/playbooks/monitor/setup_grafana.yml` - 使用 provisioning 和 dashboards

## 注意事项

1. **不要直接编辑此目录中的文件** - 它们是从 quants-lab 同步的副本
2. **需要修改配置时**：
   - 在 quants-lab 中修改源文件
   - 运行同步脚本更新此目录
3. **生产环境配置**：
   - 模板文件（*.template.yml）会被 Ansible 处理并注入实际值
   - 不要在模板中包含敏感信息（使用 Ansible 变量）
