# AudioUpdater

[![Get Hash File](https://github.com/Virace2022/AudioUpdater/actions/workflows/hash.yml/badge.svg)](https://github.com/Virace2022/AudioUpdater/actions/workflows/hash.yml)
[![Process Audio Files](https://github.com/Virace2022/AudioUpdater/actions/workflows/audio.yml/badge.svg)](https://github.com/Virace2022/AudioUpdater/actions/workflows/audio.yml)


hash.yml 获取哈希表

audio.yml 根据哈希表解包文件并上传



### Secrets: 

**R_CONFIG**: rclone配置文件， base64处理后的文本(base64 rclone.conf)
脚本中测试使用的配置名为 yandex


### Tips: 
[download.py](download.py) 依赖ManifestDownloader的联盟资源下载脚本
通过修改启动参数可自定义下载文件。