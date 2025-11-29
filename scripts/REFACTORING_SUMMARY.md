# 测试脚本重构总结 - 统一日志框架

**更新日期**: 2025-11-25  
**版本**: v3.0 (统一日志框架版本)

## 重构目标

将所有测试脚本重构为统一的日志框架，参考 `run_data_collector_logs.sh` 的优秀实践，使所有测试脚本具有：

1. **完整的日志系统** - 三种日志文件（完整、摘要、错误）
2. **详细的彩色输出** - 清晰的测试进度和结果展示
3. **前置条件检查** - AWS 凭证、SSH 密钥等
4. **成本和时间估算** - 帮助用户了解测试影响
5. **用户确认提示** - 避免意外运行昂贵测试
6. **测试时间记录** - 开始/结束时间、持续时间
7. **错误自动提取** - 快速定位问题
8. **清晰的测试摘要** - 测试结果一目了然
9. **快速命令提示** - 方便查看日志

## 重构的脚本

### 已重构 (5个)

| 脚本名称 | 测试类型 | 日志功能 | 状态 |
|---------|---------|---------|------|
| `run_infra.sh` | 基础设施测试 | ✅ 完整 | ✅ 已完成 |
| `run_security.sh` | 安全配置测试 | ✅ 完整 | ✅ 已完成 |
| `run_static_ip.sh` | 静态IP测试 | ✅ 完整 | ✅ 已完成 |
| `run_monitor.sh` | 监控系统测试 | ✅ 完整 | ⏭️ 推荐重构 |
| `run_debug.sh` | 调试测试 | ✅ 完整 | ⏭️ 推荐重构 |

### 保持原样 (4个)

| 脚本名称 | 说明 | 原因 |
|---------|------|------|
| `run_data_collector.sh` | 数据采集器测试 | 已有良好结构 |
| `run_data_collector_logs.sh` | 数据采集器测试(带日志) | 参考模板 |
| `run_comprehensive_tests.sh` | 综合测试入口 | 功能不同，无需重构 |
| `run_monitor_unit.sh` | 监控单元测试 | 轻量测试，暂不重构 |

## 统一日志框架特性

### 1. 日志文件系统

每次测试生成三个日志文件：

```bash
logs/e2e/
├── <test_type>_20251125_143022.log           # 完整日志
├── <test_type>_20251125_143022_summary.txt   # 摘要日志
└── <test_type>_20251125_143022_errors.txt    # 错误日志
```

**优势**:
- 完整日志保留所有输出，便于详细调试
- 摘要日志记录关键信息，快速回顾
- 错误日志自动提取错误，快速定位问题

### 2. 彩色输出系统

```bash
RED='\033[0;31m'      # 错误、失败
GREEN='\033[0;32m'    # 成功、通过
YELLOW='\033[1;33m'   # 警告、提示
BLUE='\033[0;34m'     # 标题、分隔符
NC='\033[0m'          # 无颜色
```

**使用示例**:
- 测试通过: `${GREEN}✓ 测试通过${NC}`
- 测试失败: `${RED}✗ 测试失败${NC}`
- 警告信息: `${YELLOW}⚠️  警告${NC}`
- 标题分隔: `${BLUE}━━━ 测试配置 ━━━${NC}`

### 3. 前置条件检查

```bash
# 检查 Conda 环境
if [[ "$CONDA_DEFAULT_ENV" != "quants-infra" ]]; then
    echo -e "${YELLOW}⚠️  请先激活 quants-infra 环境${NC}"
    exit 1
fi

# 检查 AWS 凭证
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS 凭证无效${NC}"
    exit 1
fi

# 检查 Lightsail 权限
if ! aws lightsail get-instances --region us-east-1 &>/dev/null; then
    echo -e "${RED}❌ 无 Lightsail 访问权限${NC}"
    exit 1
fi
```

### 4. 成本和时间估算

```bash
echo -e "${BLUE}成本估算${NC}"
echo -e "  预计时间: ${YELLOW}3-5 分钟${NC}"
echo -e "  预计成本: ${YELLOW}< \$0.01${NC}"
echo -e "  实例规格: ${YELLOW}nano_3_0${NC}"
```

### 5. 用户确认提示

```bash
echo -e "${YELLOW}⚠️  此测试将创建真实的 AWS 资源${NC}"
echo ""
read -p "是否继续? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}测试已取消${NC}"
    exit 0
fi
```

### 6. 测试时间记录

```bash
START_TIME=$(date +%s)
echo "测试开始时间: $(date)" > "$SUMMARY_FILE"

# ... 运行测试 ...

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_MIN=$((DURATION / 60))
DURATION_SEC=$((DURATION % 60))

echo "测试持续时间: ${DURATION_MIN}分${DURATION_SEC}秒"
```

### 7. 错误自动提取

```bash
# 从完整日志中提取错误信息
grep -E "(ERROR|FAILED|AssertionError|fatal:|Traceback)" \
  "$LOG_FILE" > "$ERROR_FILE" 2>/dev/null \
  || echo "未发现错误" > "$ERROR_FILE"

# 显示错误摘要
if [[ -s "$ERROR_FILE" ]]; then
    head -20 "$ERROR_FILE"
fi
```

### 8. 测试摘要展示

```bash
if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✓ 测试通过${NC}"
    echo ""
    echo -e "  ${GREEN}✓${NC} 所有功能正常"
else
    echo -e "${RED}✗ 测试失败 (退出码: $TEST_EXIT_CODE)${NC}"
fi

echo ""
echo -e "持续时间: ${YELLOW}${DURATION_MIN}分${DURATION_SEC}秒${NC}"
```

### 9. 快速命令提示

```bash
echo "查看完整日志:"
echo -e "  ${GREEN}cat $LOG_FILE${NC}"
echo ""
echo "查看错误日志:"
echo -e "  ${GREEN}cat $ERROR_FILE${NC}"
echo ""
echo "查看最近的日志:"
echo -e "  ${GREEN}ls -lt $LOGS_DIR | head -10${NC}"
```

## 使用示例

### 重构前 vs 重构后

#### 重构前
```bash
$ ./scripts/run_infra.sh
# 简单输出
# 日志散乱
# 错误难找
```

#### 重构后
```bash
$ ./scripts/run_infra.sh
╔══════════════════════════════════════╗
║   基础设施 E2E 测试 - 自动日志保存    ║
╚══════════════════════════════════════╝

✓ Conda 环境: quants-infra

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
测试配置
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  测试类型: 基础设施完整测试
  完整日志: logs/e2e/infra_20251125_143022.log
  摘要日志: logs/e2e/infra_20251125_143022_summary.txt
  错误日志: logs/e2e/infra_20251125_143022_errors.txt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
成本估算
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  预计时间: 3-5 分钟
  预计成本: < $0.01

⚠️  此测试将创建真实的 AWS 资源
是否继续? (y/N):
```

## 重构的好处

### 1. 调试效率提升
- **问题**: 测试失败后难以定位问题
- **解决**: 错误日志自动提取，快速定位

### 2. 测试可追溯性
- **问题**: 测试日志混乱，难以回溯
- **解决**: 三种日志文件，按时间组织

### 3. 用户体验改善
- **问题**: 不知道测试进度和成本
- **解决**: 清晰的进度显示和成本估算

### 4. 避免意外成本
- **问题**: 意外运行昂贵测试
- **解决**: 用户确认提示

### 5. 团队协作便利
- **问题**: 其他人难以理解测试结果
- **解决**: 统一格式，清晰的摘要

## 最佳实践

### 运行测试
```bash
# 使用重构后的脚本
bash scripts/run_infra.sh
bash scripts/run_security.sh
bash scripts/run_static_ip.sh
```

### 查看日志
```bash
# 查看最近的测试日志
ls -lt logs/e2e/ | head -10

# 查看特定测试的日志
cat logs/e2e/infra_20251125_143022.log

# 查看错误日志
cat logs/e2e/infra_20251125_143022_errors.txt

# 查看摘要
cat logs/e2e/infra_20251125_143022_summary.txt
```

### CI/CD 集成
```yaml
# GitHub Actions 示例
- name: Run Infrastructure Tests
  run: |
    bash scripts/run_infra.sh
    
- name: Upload Test Logs
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-logs
    path: logs/e2e/
```

## 下一步计划

### 推荐重构 (2个)
1. `run_monitor.sh` - 监控系统测试
2. `run_debug.sh` - 调试测试

### 可选重构
- `run_monitor_unit.sh` - 如果需要统一风格

## 相关文档

- [测试脚本重命名](./RENAMING_SUMMARY.md)
- [E2E 测试指南](../tests/e2e/README_E2E.md)
- [Scripts README](./README.md)

---

**维护者**: Quants Infrastructure Team  
**版本**: v3.0 (统一日志框架版本)  
**参考模板**: `run_data_collector_logs.sh`

