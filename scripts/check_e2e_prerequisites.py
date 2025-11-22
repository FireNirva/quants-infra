#!/usr/bin/env python3
"""
端到端测试前置条件检查

检查所有必要的配置和权限
"""

import os
import sys
from pathlib import Path


def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")


def print_success(message):
    """打印成功消息"""
    print(f"✓ {message}")


def print_error(message):
    """打印错误消息"""
    print(f"✗ {message}")


def print_warning(message):
    """打印警告消息"""
    print(f"⚠️  {message}")


def check_aws_credentials():
    """检查 AWS 凭证"""
    print_header("检查 AWS 凭证")
    
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        
        # 尝试获取调用者身份
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print_success("AWS 凭证已配置")
        print(f"  账户 ID: {identity['Account']}")
        print(f"  用户 ARN: {identity['Arn']}")
        print(f"  用户 ID: {identity['UserId']}")
        
        return True
        
    except NoCredentialsError:
        print_error("AWS 凭证未配置")
        print("\n请配置 AWS 凭证：")
        print("  方法 1: 环境变量")
        print("    export AWS_ACCESS_KEY_ID=your_key")
        print("    export AWS_SECRET_ACCESS_KEY=your_secret")
        print("    export AWS_DEFAULT_REGION=ap-northeast-1")
        print("\n  方法 2: AWS 凭证文件 (~/.aws/credentials)")
        print("    [default]")
        print("    aws_access_key_id = your_key")
        print("    aws_secret_access_key = your_secret")
        return False
        
    except ClientError as e:
        print_error(f"AWS 凭证验证失败: {e}")
        return False
        
    except ImportError:
        print_error("boto3 未安装")
        print("\n请安装 boto3:")
        print("  pip install boto3>=1.26")
        return False


def check_lightsail_permissions():
    """检查 Lightsail 权限"""
    print_header("检查 Lightsail 权限")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # 尝试列出实例（测试权限）
        lightsail = boto3.client('lightsail', region_name='ap-northeast-1')
        lightsail.get_instances()
        
        print_success("Lightsail 权限正常")
        
        # 检查密钥对
        try:
            response = lightsail.get_key_pairs()
            key_pairs = response.get('keyPairs', [])
            
            if key_pairs:
                print_success(f"找到 {len(key_pairs)} 个密钥对")
                for kp in key_pairs[:3]:  # 只显示前3个
                    print(f"  - {kp['name']}")
                if len(key_pairs) > 3:
                    print(f"  ... 还有 {len(key_pairs) - 3} 个")
            else:
                print_warning("未找到 Lightsail 密钥对")
                print("  测试将自动创建新密钥对")
                
        except Exception as e:
            print_warning(f"无法列出密钥对: {e}")
        
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        
        if error_code == 'AccessDeniedException':
            print_error("无 Lightsail 访问权限")
            print("\n需要以下 IAM 权限：")
            print("  - lightsail:GetInstances")
            print("  - lightsail:CreateInstances")
            print("  - lightsail:DeleteInstance")
            print("  - lightsail:GetKeyPairs")
            print("  - lightsail:CreateKeyPair")
        else:
            print_error(f"Lightsail 权限检查失败: {e}")
        
        return False
        
    except ImportError:
        print_error("boto3 未安装")
        return False


def check_conda_environment():
    """检查 Conda 环境"""
    print_header("检查 Conda 环境")
    
    conda_prefix = os.environ.get('CONDA_PREFIX')
    
    if conda_prefix:
        env_name = Path(conda_prefix).name
        print_success(f"Conda 环境已激活: {env_name}")
        
        if env_name == 'quants-infra':
            print_success("正确的环境 (quants-infra)")
            return True
        else:
            print_warning(f"当前环境是 {env_name}，建议使用 quants-infra")
            print("\n激活正确的环境:")
            print("  conda activate quants-infra")
            return True  # 仍然允许继续，只是警告
    else:
        print_error("Conda 环境未激活")
        print("\n请激活 Conda 环境:")
        print("  conda activate quants-infra")
        return False


def check_project_structure():
    """检查项目结构"""
    print_header("检查项目结构")
    
    required_dirs = [
        'core',
        'deployers',
        'providers',
        'ansible',
        'tests/e2e',
        'config/security'
    ]
    
    required_files = [
        'tests/e2e/test_security_e2e.py',
        'core/security_manager.py',
        'ansible/playbooks/security/01_initial_security.yml',
        'config/security/default_rules.yml'
    ]
    
    all_exist = True
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print_success(f"目录存在: {dir_path}")
        else:
            print_error(f"目录缺失: {dir_path}")
            all_exist = False
    
    for file_path in required_files:
        if Path(file_path).exists():
            print_success(f"文件存在: {file_path}")
        else:
            print_error(f"文件缺失: {file_path}")
            all_exist = False
    
    return all_exist


def check_python_dependencies():
    """检查 Python 依赖"""
    print_header("检查 Python 依赖")
    
    required_packages = [
        'boto3',
        'pytest',
        'ansible',
        'jinja2',
        'pyyaml'
    ]
    
    all_installed = True
    
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} 已安装")
        except ImportError:
            print_error(f"{package} 未安装")
            all_installed = False
    
    return all_installed


def estimate_cost():
    """估算测试成本"""
    print_header("测试成本估算")
    
    print("Lightsail 实例类型: nano_2_0")
    print("  - 配置: 512MB RAM, 1 vCPU, 20GB SSD")
    print("  - 价格: $0.0046/hour ($3.50/month)")
    print("")
    print("测试时间: 约 10-15 分钟")
    print("预计费用: $0.01-0.02 USD")
    print("")
    print_warning("测试会自动创建和删除实例")
    print_warning("如果测试中断，请手动删除实例以避免持续计费")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("端到端安全测试 - 前置条件检查")
    print("="*60)
    
    checks = {
        "AWS 凭证": check_aws_credentials(),
        "Lightsail 权限": check_lightsail_permissions(),
        "Conda 环境": check_conda_environment(),
        "项目结构": check_project_structure(),
        "Python 依赖": check_python_dependencies()
    }
    
    # 费用估算
    estimate_cost()
    
    # 总结
    print_header("检查总结")
    
    passed = sum(checks.values())
    total = len(checks)
    
    for name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print_success("所有检查通过！可以运行测试")
        print("\n运行测试:")
        print("  ./run_e2e_security_tests.sh")
        return 0
    else:
        print_error("部分检查未通过，请修复后重试")
        return 1


if __name__ == '__main__':
    sys.exit(main())

