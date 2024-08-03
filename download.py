# -*- coding: utf-8 -*-
# @Author  : Virace
# @Email   : Virace@aliyun.com
# @Site    : x-item.com
# @Software: Pycharm
# @Create  : 2024/8/3 4:01
# @Update  : 2024/8/3 22:01
# @Detail  : 依赖ManifestDownloader的联盟资源下载脚本

import argparse
import os
import platform
import re
import sys
import time
from operator import itemgetter

import requests
from loguru import logger
from requests.adapters import HTTPAdapter

session = requests.Session()
session.mount('https://', HTTPAdapter(max_retries=5))


def _get(url):
    try:
        res = session.get(url, timeout=10, headers={"Connection": "close"})
    except requests.exceptions.RequestException as e:
        logger.error(e)
    else:
        return res.json()


def get_game_manifest_url():
    result = {}
    for region in ['EUW1', 'PBE1']:
        releases = _get(
            f"https://sieve.services.riotcdn.net/api/v1/products/lol/version-sets/{region}?q[platform]=windows")
        # releases.raise_for_status()
        res = dict()
        for release in releases["releases"]:
            kind = release["release"]["labels"]["riot:artifact_type_id"]["values"][0]
            plat = release['release']['labels']['platform']['values']
            version = release["release"]["labels"]["riot:artifact_version_id"]["values"][0].split("+")[0]
            if 'lol-game-client' == kind and 'windows' in plat:
                res[version] = release["download"]["url"]

        r = [[int(i) for i in item.split('.')] for item in res.keys()]
        temp = sorted(r, key=itemgetter(0, 1))[-1]
        res_ver = '.'.join([str(item) for item in temp])
        _t = 'live'
        if 'PBE' in region:
            _t = 'pbe'
        result.update({_t: dict(version=res_ver, patch_url=res[res_ver])})

    return result


def get_lcu_manifest_url(region='EUW'):
    client_releases = _get(
        "https://clientconfig.rpg.riotgames.com/api/v1/config/public?namespace=keystone.products.league_of_legends.patchlines")
    # client_releases.raise_for_status()
    # ["keystone.products.league_of_legends.patchlines.live", "keystone.products.league_of_legends.patchlines.pbe"]
    result = {}
    for key, patchline in client_releases.items():
        for configuration in patchline["platforms"]["win"]["configurations"]:
            if configuration["id"] in [region, 'PBE']:
                # configurations.append((region, configuration["patch_url"]))
                data = configuration['metadata']['theme_manifest'].split('/')[-3], configuration["patch_url"]
                _t = key.split('.')[-1]
                result.update({_t: dict(version=data[0], patch_url=data[-1])})
    return result


def download(outpath, logpath, game_filter, lcu_filter, max_retries, mbin='./ManifestDownloader'):
    game_url = get_game_manifest_url()
    lcu_url = get_lcu_manifest_url()
    logger.info(f"live version: {game_url['live']['version']}")
    logger.debug(f'GAME: {game_url}, LCU: {lcu_url}')
    g_log = os.path.join(logpath, 'game.log')
    l_log = os.path.join(logpath, 'lcu.log')

    retry = 0
    success = False

    while retry < max_retries and not success:
        logger.info(f"Start download attempt {retry + 1}")

        # 版本
        # os.system(
        #     f'{mbin} {game_url["live"]["patch_url"]} -o "{outpath}" -t 8  -f "content-metadata.json" > {g_log}')
        os.system(
            f'{mbin} {game_url["live"]["patch_url"]} -o "{os.path.join(outpath, "Game")}" -t 8  -f "{game_filter}|content-metadata.json" >> {g_log}')
        os.system(
            f'{mbin} {lcu_url["live"]["patch_url"]} -o "{os.path.join(outpath, "LeagueClient")}" -t 8  -f "{lcu_filter}" > {l_log}')

        # 检查下载是否成功
        with open(g_log, 'r') as f:
            game_log = f.read()
            logger.info(game_log)

        with open(l_log, 'r') as f:
            lcu_log = f.read()
            logger.info(lcu_log)

        combined_log = game_log + lcu_log
        if any(key in combined_log.lower() for key in ['error', 'aborted', 'failed', 'closed', 'not']):
            retry += 1
            logger.warning(f"Download error, retrying ({retry}/{max_retries})")
            time.sleep(5)
        else:
            success = True
            logger.info("Download success")

    if not success:
        logger.error("Retry limit reached, download failed")
        # 有必要可以将日志上传 upload-artifact
        raise Exception('Retry limit reached, download failed')


def process_type_arguments(args_type, type_map, type_name):
    """
    正则参数 校验
    :param args_type:
    :param type_map:
    :param type_name:
    :return:
    """
    filters = []
    for item in args_type:
        if item in type_map:
            filters.append(type_map[item])
        else:
            try:
                re.compile(item)  # 检查正则表达式是否合法
                filters.append(item)
            except re.error:
                logger.error(f"无效的{type_name}正则表达式 '{item}'")
                sys.exit(1)
    return filters


def get_absolute_path(path):
    """
    相对转绝对
    :param path:
    :return:
    """
    if not os.path.isabs(path):
        return os.path.abspath(path)
    return path


def main():
    # 根据系统类型设置默认的 ManifestDownloader 可执行文件名
    if platform.system() == "Windows":
        default_manifest_downloader = "ManifestDownloader.exe"
    else:
        default_manifest_downloader = "ManifestDownloader"

    # 初始化参数解析器
    parser = argparse.ArgumentParser(description="下载资源的脚本")

    # 添加参数
    parser.add_argument(
        "-g", "--game_type",
        type=str,
        nargs='+',
        default=[],
        help='游戏资源下载类型: 可以组合使用 "c"（英雄资源）、 "cz"（英雄zh_CN音频资源）、 "m"（地图资源）、 "mz"（地图zh_CN音频资源）、 自定义正则。例如: -g c m 或 -g c "自定义正则"'
    )

    parser.add_argument(
        "-l", "--lcu_type",
        type=str,
        nargs='+',
        default=[],
        help='LCU资源下载类型: 可以组合使用 "l"（LCU DATA）、 "lz"（LCU zh_CN资源）、 自定义正则。例如: -l l lz 或 -l "自定义正则"'
    )

    parser.add_argument(
        "-o", "--outpath",
        type=str,
        default="outpath",
        help="输出目录"
    )

    parser.add_argument(
        "-d", "--logdir",
        type=str,
        default="logs",
        help="日志目录"
    )

    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=5,
        help="重试次数"
    )

    parser.add_argument(
        "-m", "--manifest_downloader",
        type=str,
        default=default_manifest_downloader,
        help="ManifestDownloader 程序可执行文件"
    )

    # 解析参数
    args = parser.parse_args()

    # 设置日志记录
    logger.add(os.path.join(args.logdir, "script.log"), rotation="500 MB")

    # 检查 manifest_downloader 可执行文件是否存在
    args.manifest_downloader = get_absolute_path(args.manifest_downloader)
    if not os.path.isfile(args.manifest_downloader) and not os.path.exists(args.manifest_downloader):
        logger.error(f"ManifestDownloader 可执行文件 '{args.manifest_downloader}' 不存在。")
        parser.print_help()
        sys.exit(1)

    # 检查 game_type 和 lcu_type 是否为空
    if not args.game_type and not args.lcu_type:
        logger.error("游戏资源和 LCU 资源下载类型不能同时为空。")
        parser.print_help()
        sys.exit(1)

    game_type_map = {
        'c': r"DATA/FINAL/Champions/\w+.wad.client",
        'cz': r"DATA/FINAL/Champions/\w+.zh_CN.wad.client",
        'm': r"DATA/FINAL/Maps/Shipping/\w+.wad.client",
        'mz': r"DATA/FINAL/Maps/Shipping/\w+.zh_CN.wad.client"
    }

    lcu_type_map = {
        'l': r"Plugins/rcp-be-lol-game-data/default-assets.wad",
        'lz': r"Plugins/rcp-be-lol-game-data/zh_CN-assets.wad"
    }

    # 处理游戏资源下载类型参数
    game_filters = process_type_arguments(args.game_type, game_type_map, "GAME")

    # 处理LCU资源下载类型参数
    lcu_filters = process_type_arguments(args.lcu_type, lcu_type_map, "LCU")

    game_combined_filter = "|".join(game_filters)
    lcu_combined_filter = "|".join(lcu_filters)
    args.outpath = get_absolute_path(args.outpath)
    args.logdir = get_absolute_path(args.logdir)

    # 打印参数（用于测试）
    logger.info(f"游戏资源下载类型: {args.game_type}")
    logger.info(f"LCU资源下载类型: {args.lcu_type}")
    logger.info(f"输出目录: {args.outpath}")
    logger.info(f"日志目录: {args.logdir}")
    logger.info(f"重试次数: {args.retries}")
    logger.info(f"ManifestDownloader 可执行文件: {args.manifest_downloader}")

    # 打印合并后的过滤器（用于测试）
    logger.debug(f"使用的GAME过滤器: {game_combined_filter}")
    logger.debug(f"使用的LCU过滤器: {lcu_combined_filter}")

    os.makedirs(args.outpath, exist_ok=True)
    os.makedirs(args.logdir, exist_ok=True)

    download(args.outpath, args.logdir, game_combined_filter, lcu_combined_filter, args.retries,
             args.manifest_downloader)


if __name__ == '__main__':
    main()
