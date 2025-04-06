import os

from flask import Flask, render_template, jsonify
import psutil
import time
import platform

app = Flask(__name__)


def get_download_speed(interval=0.2, interface=None):
    """
    获取当前网络下载速率
    :param interval: 采样间隔时间（秒）
    :param interface: 指定网络接口（如 'eth0'），默认获取所有接口总和
    :return: 下载速率（Mbps）
    """
    # 第一次获取网络IO数据
    if interface:
        io_before = psutil.net_io_counters(pernic=True).get(interface)
        if not io_before:
            raise ValueError(f"接口 {interface} 不存在")
        bytes_before = io_before.bytes_recv
    else:
        bytes_before = psutil.net_io_counters().bytes_recv

    time.sleep(interval)

    # 第二次获取网络IO数据
    if interface:
        io_after = psutil.net_io_counters(pernic=True).get(interface)
        bytes_after = io_after.bytes_recv
    else:
        bytes_after = psutil.net_io_counters().bytes_recv

    # 计算速率并转换单位
    speed_bps = (bytes_after - bytes_before) * 8  # 转换为比特
    speed_mbps = speed_bps / (interval * 10 ** 6)  # 转换为 Mbps
    return speed_mbps


def get_upload_speed(interval=0.2, interface=None):
    """
    获取当前网络上传速率
    :param interval: 采样间隔时间（秒）
    :param interface: 指定网络接口（如 'eth0'），默认获取所有接口总和
    :return: 上传速率（Mbps）
    """
    # 第一次获取网络IO数据
    if interface:
        io_before = psutil.net_io_counters(pernic=True).get(interface)
        if not io_before:
            raise ValueError(f"接口 {interface} 不存在")
        bytes_before = io_before.bytes_sent  # 关键：使用 bytes_sent
    else:
        bytes_before = psutil.net_io_counters().bytes_sent

    time.sleep(interval)

    # 第二次获取网络IO数据
    if interface:
        io_after = psutil.net_io_counters(pernic=True).get(interface)
        bytes_after = io_after.bytes_sent
    else:
        bytes_after = psutil.net_io_counters().bytes_sent

    # 计算速率并转换单位
    speed_bps = (bytes_after - bytes_before) * 8  # 转换为比特
    speed_mbps = speed_bps / (interval * 10 ** 6)  # 转换为 Mbps
    return speed_mbps


def get_system_uptime():
    """
    获取系统开机后的运行时间（天、小时、分钟）
    Returns:
        tuple: (days, hours, minutes)
    """
    # 获取系统启动时间的时间戳（UTC）
    boot_time = psutil.boot_time()

    # 获取当前时间戳
    now = time.time()

    # 计算运行时间（秒）
    uptime_seconds = now - boot_time

    # 转换为天、小时、分钟
    days, remainder = divmod(uptime_seconds, 86400)  # 1天=86400秒
    hours, remainder = divmod(remainder, 3600)  # 1小时=3600秒
    minutes = remainder // 60  # 1分钟=60秒

    return int(days), int(hours), int(minutes)


def get_total_storage():
    """获取系统总存储容量（单位：GB）"""
    total_bytes = 0
    seen_devices = set()  # 用于设备去重

    # 排除的虚拟文件系统类型
    excluded_fs_types = {
        'tmpfs', 'proc', 'devtmpfs', 'sysfs',
        'overlay', 'aufs', 'squashfs', 'none'
    }

    for part in psutil.disk_partitions(all=False):
        # 跳过虚拟文件系统和重复设备
        if part.fstype in excluded_fs_types:
            continue

        # Windows 特殊处理：通过设备路径去重
        if psutil.WINDOWS:
            device = part.device.split('\\')[0]  # 取驱动器字母（如 "C:"）
            if device in seen_devices:
                continue
            seen_devices.add(device)
        else:
            # Linux/Mac 通过设备名去重（如 "/dev/disk1"）
            if part.device in seen_devices:
                continue
            seen_devices.add(part.device)

        try:
            usage = psutil.disk_usage(part.mountpoint)
            total_bytes += usage.total
        except Exception as e:
            print(f"Warning: 无法获取 {part.mountpoint} 的存储信息 ({str(e)})")

    # 字节转GB（1GB = 1024^3 bytes）
    return round(total_bytes / (1024 ** 3), 1)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/system-stats')
def info():
    cpu_use = psutil.cpu_percent(interval=0.2)
    mem_use = psutil.virtual_memory().percent
    disk_use = psutil.disk_usage('/').percent
    dspeed = '{:.2f}'.format(get_download_speed(interval=0.2))
    uspeed = '{:.2f}'.format(get_upload_speed(interval=0.2))
    days, hours, minutes = get_system_uptime()
    cpu_model = platform.machine()
    cpu_cores = psutil.cpu_count()
    cpu_arch = platform.architecture()
    os_version = platform.system() + ' ' + platform.version().split()[0]
    total_memory = psutil.virtual_memory().total / 1024 / 1024
    virtual_memory = psutil.swap_memory().total / 1024 / 1024
    total_storage = get_total_storage()
    data = {
        "cpu_use": cpu_use,
        "mem_use": mem_use,
        "disk_use": disk_use,
        "dspeed": dspeed,
        "uspeed": uspeed,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        'cpu_model': cpu_model,
        'cpu_cores': cpu_cores,
        'cpu_arch': cpu_arch,
        'os_version': os_version,
        'total_memory': total_memory,
        'virtual_memory': virtual_memory,
        'total_storage':total_storage
    }
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=False, port=8999, threaded=True)
