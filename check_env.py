import sys
import platform
import pkg_resources
import os

def check_python_env():
    print(f"Python版本: {sys.version}")
    print(f"\n操作系统: {platform.platform()}")
    
    print("\n已安装的主要包:")
    installed_packages = [dist.project_name for dist in pkg_resources.working_set]
    for pkg in sorted(installed_packages):
        version = pkg_resources.get_distribution(pkg).version
        print(f"- {pkg}: {version}")

    print(f"\nPython可执行文件位置: {sys.executable}")
    
    if 'VIRTUAL_ENV' in os.environ:
        print(f"\n当前虚拟环境: {os.environ['VIRTUAL_ENV']}")
    else:
        print("\n未检测到虚拟环境")

if __name__ == "__main__":
    check_python_env() 