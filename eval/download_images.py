"""Download open-source fashion photos from Pexels into eval/images/."""

from __future__ import annotations

import urllib.request
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; FashionInspirationEval/1.0)"

# Curated Pexels fashion / street-style photo IDs (free to use per Pexels license)
PHOTO_IDS = [
    6311392, 985635, 1536619, 1884581, 2673506, 298346, 1126993, 1036623,
    1308881, 1485031, 206359, 1926769, 3373736, 5813392, 6311575, 6311655,
    6311584, 7680060, 7679569, 6311397, 6311652, 7679861, 7679723, 7680142,
    996329, 994523, 994517, 175538, 1464625, 157675, 1828537, 2830509,
    2830503, 3755511, 3984877, 4004170, 4210863, 4380970, 4458370, 4482900,
    4646824, 4939447, 4943165, 4946416, 5050837, 5060469, 5081385, 5094830,
    5122169, 5143142, 5206946, 5256744,
    1040945, 1018918, 1021693, 1045541, 1080868, 1183266, 1223763, 1280063,
]

OUT = Path(__file__).parent / "images"


def url(photo_id: int) -> str:
    return (
        f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg"
        f"?auto=compress&cs=tinysrgb&w=960"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i, photo_id in enumerate(PHOTO_IDS, start=1):
        dest = OUT / f"fashion-{i:03d}.jpg"
        if dest.exists() and dest.stat().st_size > 10_000:
            ok += 1
            continue
        try:
            req = urllib.request.Request(url(photo_id), headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp, dest.open("wb") as out:
                out.write(resp.read())
            ok += 1
            print(f"saved {dest.name}")
        except Exception as err:
            print(f"skip {photo_id}: {err}")
    print(f"done — {ok}/{len(PHOTO_IDS)} images in {OUT}")


if __name__ == "__main__":
    main()
