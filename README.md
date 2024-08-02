# AudioUpdater

定时执行hash.yml，从Aatrox.wad.client等文件中获取音频哈希表

执行成功触发audio.yml，在根据上述获取的哈希表从Aatrox.zh_CN.wad.client中提取音频上传到oss



不涉及地图等音频，则暂时无需考虑文件大小。
效果音建议本地或VPS中执行，因为文件过多执行时间过长。