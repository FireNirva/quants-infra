#!/bin/bash
# 同步监控配置脚本
# 从 quants-lab 复制监控配置到 infrastructure 项目

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INFRA_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
QUANTS_LAB_ROOT="$( cd "$INFRA_ROOT/../quants-lab" && pwd )"

# 目标目录
INFRA_CONFIG_DIR="$INFRA_ROOT/config/monitoring"
QUANTS_LAB_CONFIG_DIR="$QUANTS_LAB_ROOT/config"

# 打印帮助信息
print_help() {
    cat << EOF
监控配置同步脚本

用法:
    $(basename "$0") [OPTIONS]

选项:
    --copy          复制文件（默认）
    --symlink       创建软链接
    --check         检查配置是否已同步
    --force         强制覆盖现有文件
    -h, --help      显示帮助信息

说明:
    此脚本用于同步 quants-lab 项目中的监控配置到 infrastructure 项目。
    
    源目录: $QUANTS_LAB_CONFIG_DIR
    目标目录: $INFRA_CONFIG_DIR

同步内容:
    - Prometheus 配置和告警规则
    - Alertmanager 配置
    - Grafana provisioning 和 dashboards

示例:
    # 复制配置文件
    $(basename "$0") --copy

    # 创建软链接（开发推荐）
    $(basename "$0") --symlink

    # 检查配置同步状态
    $(basename "$0") --check

EOF
}

# 检查源目录是否存在
check_source_dir() {
    if [ ! -d "$QUANTS_LAB_CONFIG_DIR" ]; then
        echo -e "${RED}❌ 错误: 未找到 quants-lab 配置目录${NC}"
        echo "   路径: $QUANTS_LAB_CONFIG_DIR"
        exit 1
    fi
    echo -e "${GREEN}✅ 找到源配置目录${NC}"
}

# 创建目标目录
create_target_dirs() {
    echo -e "${BLUE}📁 创建目标目录...${NC}"
    
    mkdir -p "$INFRA_CONFIG_DIR/prometheus"
    mkdir -p "$INFRA_CONFIG_DIR/alertmanager"
    mkdir -p "$INFRA_CONFIG_DIR/grafana/provisioning/datasources"
    mkdir -p "$INFRA_CONFIG_DIR/grafana/provisioning/dashboards"
    mkdir -p "$INFRA_CONFIG_DIR/grafana/dashboards"
    
    echo -e "${GREEN}✅ 目录创建完成${NC}"
}

# 复制配置文件
copy_configs() {
    local force=$1
    echo -e "${BLUE}📋 复制配置文件...${NC}"
    
    # Prometheus 配置
    echo "  - alert_rules.yml"
    if [ "$force" = true ] || [ ! -f "$INFRA_CONFIG_DIR/prometheus/alert_rules.yml" ]; then
        cp "$QUANTS_LAB_CONFIG_DIR/alert_rules.yml" "$INFRA_CONFIG_DIR/prometheus/"
        echo -e "    ${GREEN}✓${NC} 已复制"
    else
        echo -e "    ${YELLOW}⊘${NC} 已存在（使用 --force 覆盖）"
    fi
    
    echo "  - prometheus_multiport.yml (作为模板)"
    if [ "$force" = true ] || [ ! -f "$INFRA_CONFIG_DIR/prometheus/prometheus.template.yml" ]; then
        cp "$QUANTS_LAB_CONFIG_DIR/prometheus/prometheus_multiport.yml" \
           "$INFRA_CONFIG_DIR/prometheus/prometheus.template.yml"
        echo -e "    ${GREEN}✓${NC} 已复制"
    else
        echo -e "    ${YELLOW}⊘${NC} 已存在（使用 --force 覆盖）"
    fi
    
    # Alertmanager 配置
    echo "  - alertmanager.yml"
    if [ "$force" = true ] || [ ! -f "$INFRA_CONFIG_DIR/alertmanager/alertmanager.template.yml" ]; then
        cp "$QUANTS_LAB_CONFIG_DIR/alertmanager.yml" \
           "$INFRA_CONFIG_DIR/alertmanager/alertmanager.template.yml"
        echo -e "    ${GREEN}✓${NC} 已复制"
    else
        echo -e "    ${YELLOW}⊘${NC} 已存在（使用 --force 覆盖）"
    fi
    
    # Grafana provisioning
    echo "  - Grafana provisioning 配置"
    if [ -d "$QUANTS_LAB_CONFIG_DIR/grafana/provisioning" ]; then
        if [ "$force" = true ]; then
            rm -rf "$INFRA_CONFIG_DIR/grafana/provisioning"/*
        fi
        cp -r "$QUANTS_LAB_CONFIG_DIR/grafana/provisioning/"* \
              "$INFRA_CONFIG_DIR/grafana/provisioning/"
        echo -e "    ${GREEN}✓${NC} 已复制"
    fi
    
    # Grafana dashboards
    echo "  - Grafana dashboards"
    if [ -d "$QUANTS_LAB_CONFIG_DIR/grafana/dashboards" ]; then
        if [ "$force" = true ]; then
            rm -rf "$INFRA_CONFIG_DIR/grafana/dashboards"/*
        fi
        cp -r "$QUANTS_LAB_CONFIG_DIR/grafana/dashboards/"* \
              "$INFRA_CONFIG_DIR/grafana/dashboards/" 2>/dev/null || true
        echo -e "    ${GREEN}✓${NC} 已复制"
    fi
    
    # 创建 README
    cat > "$INFRA_CONFIG_DIR/README.md" << 'EOF'
# 监控配置目录

此目录包含从 `quants-lab/config/` 同步的监控配置文件。

## 配置来源

所有监控配置都来源于 `quants-lab` 项目，使用以下脚本同步：

```bash
quants-infra/scripts/sync_monitoring_configs.sh
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
cd quants-infra
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
EOF
    
    echo -e "${GREEN}✅ 配置文件复制完成${NC}"
}

# 创建软链接
create_symlinks() {
    local force=$1
    echo -e "${BLUE}🔗 创建软链接...${NC}"
    
    # Prometheus alert_rules.yml
    local target="$QUANTS_LAB_CONFIG_DIR/alert_rules.yml"
    local link="$INFRA_CONFIG_DIR/prometheus/alert_rules.yml"
    
    if [ "$force" = true ] && [ -e "$link" ]; then
        rm -f "$link"
    fi
    
    if [ ! -e "$link" ]; then
        ln -s "$target" "$link"
        echo -e "  ${GREEN}✓${NC} alert_rules.yml"
    else
        echo -e "  ${YELLOW}⊘${NC} alert_rules.yml 已存在"
    fi
    
    # Grafana provisioning
    local target_prov="$QUANTS_LAB_CONFIG_DIR/grafana/provisioning"
    local link_prov="$INFRA_CONFIG_DIR/grafana/provisioning_linked"
    
    if [ "$force" = true ] && [ -e "$link_prov" ]; then
        rm -f "$link_prov"
    fi
    
    if [ ! -e "$link_prov" ]; then
        ln -s "$target_prov" "$link_prov"
        echo -e "  ${GREEN}✓${NC} grafana/provisioning"
    else
        echo -e "  ${YELLOW}⊘${NC} grafana/provisioning 已存在"
    fi
    
    # Grafana dashboards
    local target_dash="$QUANTS_LAB_CONFIG_DIR/grafana/dashboards"
    local link_dash="$INFRA_CONFIG_DIR/grafana/dashboards_linked"
    
    if [ "$force" = true ] && [ -e "$link_dash" ]; then
        rm -f "$link_dash"
    fi
    
    if [ ! -e "$link_dash" ] && [ -d "$target_dash" ]; then
        ln -s "$target_dash" "$link_dash"
        echo -e "  ${GREEN}✓${NC} grafana/dashboards"
    else
        echo -e "  ${YELLOW}⊘${NC} grafana/dashboards 已存在或源不存在"
    fi
    
    echo -e "${GREEN}✅ 软链接创建完成${NC}"
}

# 检查配置同步状态
check_sync_status() {
    echo -e "${BLUE}🔍 检查配置同步状态...${NC}"
    echo ""
    
    local all_synced=true
    
    # 检查必要文件
    local files=(
        "prometheus/alert_rules.yml"
        "prometheus/prometheus.template.yml"
        "alertmanager/alertmanager.template.yml"
    )
    
    for file in "${files[@]}"; do
        local path="$INFRA_CONFIG_DIR/$file"
        if [ -e "$path" ]; then
            if [ -L "$path" ]; then
                echo -e "  ${BLUE}🔗${NC} $file (软链接)"
            else
                echo -e "  ${GREEN}✓${NC} $file"
            fi
        else
            echo -e "  ${RED}✗${NC} $file (缺失)"
            all_synced=false
        fi
    done
    
    echo ""
    if [ "$all_synced" = true ]; then
        echo -e "${GREEN}✅ 所有配置文件已同步${NC}"
    else
        echo -e "${RED}⚠️  部分配置文件缺失，请运行同步脚本${NC}"
        echo "   ./scripts/sync_monitoring_configs.sh --copy"
    fi
}

# 主函数
main() {
    # 默认选项
    MODE="copy"
    FORCE=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --copy)
                MODE="copy"
                shift
                ;;
            --symlink)
                MODE="symlink"
                shift
                ;;
            --check)
                MODE="check"
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            -h|--help)
                print_help
                exit 0
                ;;
            *)
                echo -e "${RED}❌ 未知选项: $1${NC}"
                print_help
                exit 1
                ;;
        esac
    done
    
    # 检查源目录
    check_source_dir
    
    # 根据模式执行
    case $MODE in
        copy)
            create_target_dirs
            copy_configs $FORCE
            echo ""
            echo -e "${GREEN}✅ 配置同步完成！${NC}"
            ;;
        symlink)
            create_target_dirs
            create_symlinks $FORCE
            echo ""
            echo -e "${GREEN}✅ 软链接创建完成！${NC}"
            echo -e "${YELLOW}⚠️  注意: 修改源文件会立即影响此项目${NC}"
            ;;
        check)
            check_sync_status
            ;;
    esac
}

# 运行主函数
main "$@"

