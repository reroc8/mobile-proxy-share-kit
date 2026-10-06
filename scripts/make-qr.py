#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 docs/assets/ 下的两张二维码，生成后立刻解码回读校验。

为什么要有脚本而不是手工生成
----------------------------
二维码的内容错了，是要等用户扫了才发现 —— 而且扫的人多半不会告诉你。
所以内容在这里集中定义一次，并规定：改二维码只能改这个脚本、重跑它，不要手工替换 PNG。

两张码用途不同，别搞混：

* `shadowrocket-config-qr.png` —— 内容是 `shadowrocket://config/add/{配置地址}`。
  **用 Shadowrocket 自带的扫码**扫它，直接下载并启用配置。
  参照同类项目做法：`Johnshall/Shadowrocket-ADBlock-Rules-Forever` 的二维码解码出来
  就是同样的 `shadowrocket://config/add/https://...` 形式。
  注意：这个 scheme 不能用 iOS 系统相机扫（相机只认 http/https 等固定类型），
  必须用 App 内的扫码。

依赖（只在本机生成时用，不属于运行时依赖）：
    pip install segno opencv-python-headless

用法：
    python3 scripts/make-qr.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent

RAW_BASE = "https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main"
PAGES_BASE = "https://reroc8.github.io/mobile-proxy-share-kit"

# 文件名是中文，URL 里必须百分号编码 —— 未编码的 `星君分流.conf` 会让 iOS 的 URL 解析失败。
# 小火箭拿到编码后的 URL 去下载，取显示名时会自行解码（这一点待真机确认）。
SHADOWROCKET_CONFIG = f"{RAW_BASE}/shadowrocket/{quote('星君分流.conf')}"
SHADOWROCKET_SCHEME = f"shadowrocket://config/add/{SHADOWROCKET_CONFIG}"
# (输出文件, 二维码内容, 说明)
# 只做一张：能被小火箭直接扫码导入的配置码。
# 曾经还有第二张「入口码」指向手机操作页，但那样等于「扫码 → 打开网页 → 网页上再扫一次」，
# 绕两圈。一张码直达就够了。
QRCODES = (
    ("docs/assets/shadowrocket-config-qr.png", SHADOWROCKET_SCHEME, "小火箭扫码导入（用 App 内扫码）"),
)


def main() -> int:
    try:
        import segno
    except ImportError:
        print("错误: 需要 segno。pip install segno", file=sys.stderr)
        return 1

    try:
        import cv2
    except ImportError:
        cv2 = None
        print("提示: 没有 opencv，跳过解码回读校验。建议装上：pip install opencv-python-headless")

    detector = cv2.QRCodeDetector() if cv2 else None
    failed = 0

    for relative, payload, note in QRCODES:
        path = REPO_ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        segno.make(payload, error="m").save(path, scale=8, border=2)
        print(f"已生成: {relative}")
        print(f"        用途: {note}")
        print(f"        内容: {payload}")

        if detector is None:
            continue

        decoded, _, _ = detector.detectAndDecode(cv2.imread(str(path)))
        if decoded == payload:
            print("        回读校验: 通过")
        else:
            failed += 1
            print(f"        回读校验: 失败，解出来是 {decoded!r}", file=sys.stderr)
        print()

    if failed:
        print(f"错误: {failed} 张二维码校验不通过", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
