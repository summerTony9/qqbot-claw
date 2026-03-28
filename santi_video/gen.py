#!/usr/bin/env python3
"""Generate images and TTS audio for 三体II 序章 口播视频"""

import asyncio
import base64
import os
import httpx
import json
from datetime import datetime

API_KEY = "sk-cp-9wukxy8LSWgiOkA4g0z637Jz7yHn5b4Cg_QnbO8UN-5cVVbw7bw3Mzg83QsD4xAbG_fRq4V829GE5UVYFBGhSAinJbKw9c0VU_1A6Opgg8cezUgrhQqlNOg"
OUTPUT_DIR = "/root/.openclaw/workspace/santi_video"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Image prompts for each scene
IMAGE_PROMPTS = [
    {
        "id": "01_ant",
        "prompt": "A microscopic perspective of a tiny brown ant climbing a towering black mountain peak in twilight. The peak is enormous and ominous, casting a dramatic shadow. Below the mountain stretches an endless dark plain. In the far distance, a few faint stars appear in the darkening sky. Cinematic, dramatic lighting, photorealistic, viewed from the ant's tiny scale. 暮色中的黑色孤峰脚下, 一只渺小的褐蚁正在攀爬光滑的岩壁, 蚂蚁的视角, 微小与巨大的对比, 电影感, 写实风格"
    },
    {
        "id": "02_cliff",
        "prompt": "A mysterious woman with gray hair and a young man standing on top of a black jagged cliff at dusk. The woman is looking into the distance, the young man seems confused. Behind them an endless dark wilderness stretches out. Cold color palette, twilight sky with deep blue and purple tones, stars beginning to appear. Cinematic composition, atmospheric, Chinese sci-fi style. 两位人物站在黑色荒原的悬崖边, 一位白发女性和一位年轻男子, 黄昏时分, 星空开始出现, 苍凉孤独的氛围, 电影感"
    },
    {
        "id": "03_ship",
        "prompt": "A massive cargo ship called '审判日号' sailing through the dark Pacific Ocean at night. The ship is bathed in cold moonlight. In the distance, the Milky Way stretches across the night sky. A man stands alone at the bow of the ship, his silhouette backlit by starlight, gazing into the deep ocean. Cinematic, dramatic, photorealistic, epic scale. 夜色中的太平洋, 一艘巨大的货船破浪而行, 船头站着一个孤独的人影, 星空倒映在黑丝绒般的海面上, 神秘而苍凉, 电影感"
    },
    {
        "id": "04_aliens",
        "prompt": "Split screen: Left side shows a transparent alien head with glowing neural pathways visible inside, their thoughts displayed as floating text in the air. Right side shows a human head with dark swirling thoughts hidden behind a mask-like face, question marks and mysteries swirling inside. Between them, floating Chinese characters '想' and '说' connected by an equals sign. Sci-fi concept art, dark background, ethereal glowing elements. 科幻概念图: 左半边透明外星人的思维暴露在外, 右半边人类思维隐藏在迷雾中, 对比设计, 深色背景, 光芒效果"
    },
    {
        "id": "05_stars",
        "prompt": "A vast cosmic scene: billions of stars scattered across the universe like grains of sand. In the center, a faint pale blue dot barely visible - Earth. Around it, dark forest of unknown dangers lurking. A single beam of light from Earth trying to reach the stars. Epic scale, cosmic perspective, haunting and lonely atmosphere. 宇宙星空, 繁星如沙, 中间一个暗淡的蓝点代表地球, 孤独地悬浮在黑暗中, 宇宙的黑暗森林感, 史诗级科幻场景"
    }
]

# TTS narration segments - split by scene
NARRATION_SEGMENTS = [
    {
        "id": "01_ant",
        "emotion": "sad",
        "text": "这个星球上，有两种眼睛。一种，是地底下那只褐蚁。它渺小，卑微，抬起头也望不见天空的边界。它只是爬，漫无目的地爬。黑色的孤峰拔地而起，挡在它面前，它就顺着岩壁向上。不是为了抵达，只是神经里一次微不足道的扰动。它不知道的是，此刻在它脚下，有两个即将改变人类命运的人，正站在崖边对话。"
    },
    {
        "id": "02_cliff",
        "emotion": "calm",
        "text": "山顶上，褐蚁俯瞰着两个人类的相遇。她叫叶文洁，白发在暮色中格外醒目。他叫罗辑，一个天文转社会学的年轻人，聪明，但心很散。一个已经失去了女儿，一个还不知道为什么活着。他们相遇在这片荒原的孤峰下，说着些看似无关紧要的话。但正是这些无关紧要的话，悄悄地推动了人类的命运。叶文洁说：宇宙中分布着数量巨大的文明，它们的数目与能观测到的星星是一个数量级。很多很多。这就是宇宙社会学。"
    },
    {
        "id": "03_ship",
        "emotion": "serious",
        "text": "另一种眼睛，在太平洋的夜海上。审判日号，劈开黑色的浪，船上站着一个男人。他叫伊文斯。富二代，美国石油大亨的儿子。他手握一根细细的线，连接着四光年外的另一个文明。此刻他正与那个世界进行最后一次对话。字幕亮起，冷冰冰的，没有温度。那是另一个世界的声音。"
    },
    {
        "id": "04_deception",
        "emotion": "scare",
        "text": "字幕说：你们人类有一个词，我们始终无法理解。伊文斯问：哪个词？字幕回答：欺骗。伊文斯愣住了。他给三体人讲了小红帽的故事——狼装成外婆，骗孩子们开门。多么简单的骗局。但三体人完全无法理解。它们说：狼为什么要交流？它直接进去吃不就行了？伊文斯恍然大悟。他们的文明里没有谎言。思维是全透明的，像一本摊开的书。想，就是说。说，就是想。对他们而言，欺骗，根本不存在。"
    },
    {
        "id": "05_end",
        "emotion": "sad",
        "text": "伊文斯抬起头，望向星空。他终于明白了一件事。地球人最强大的武器，不是飞船，不是核弹——是谎言。字幕再次亮起。这一次，只有短短五个字。字幕说：我害怕你们。画面渐黑。这就是序章。一只蚂蚁，两个失意的人，一段跨越四光年的对话，以及一个文明最深的恐惧。故事，才刚刚开始。"
    }
]

async def generate_image(session: httpx.AsyncClient, prompt_data: dict) -> dict:
    """Generate a single image"""
    payload = {
        "model": "image-01",
        "prompt": prompt_data["prompt"],
        "aspect_ratio": "16:9",
        "response_format": "url",
        "n": 1,
        "prompt_optimizer": True,
    }
    try:
        resp = await session.post(
            "https://api.minimaxi.com/v1/image_generation",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        image_urls = (((data or {}).get("data") or {}).get("image_urls")) or []
        if image_urls:
            return {"id": prompt_data["id"], "url": image_urls[0], "success": True}
    except Exception as e:
        print(f"Image {prompt_data['id']} failed: {e}")
    return {"id": prompt_data["id"], "url": None, "success": False}

async def generate_tts(session: httpx.AsyncClient, segment: dict) -> dict:
    """Generate TTS audio for a narration segment"""
    payload = {
        "model": "speech-2.8-hd",
        "text": segment["text"],
        "stream": False,
        "voice_setting": {
            "voice_id": "male-qn-qingse",
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": segment["emotion"]
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3"
        }
    }
    try:
        resp = await session.post(
            "https://api.minimaxi.com/v1/t2a_v2",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        audio_hex = (((data or {}).get("data") or {}).get("audio")) or ""
        if audio_hex:
            audio_bytes = bytes.fromhex(audio_hex)
            filename = f"{OUTPUT_DIR}/audio_{segment['id']}.mp3"
            with open(filename, "wb") as f:
                f.write(audio_bytes)
            return {"id": segment["id"], "file": filename, "success": True}
    except Exception as e:
        print(f"TTS {segment['id']} failed: {e}")
    return {"id": segment["id"], "file": None, "success": False}

async def main():
    print("=== Starting generation ===")
    async with httpx.AsyncClient() as session:
        # Generate all 5 images in parallel
        print("Generating 5 images in parallel...")
        image_tasks = [generate_image(session, p) for p in IMAGE_PROMPTS]
        image_results = await asyncio.gather(*image_tasks)
        
        print("Generating 5 TTS audio segments in parallel...")
        tts_tasks = [generate_tts(session, s) for s in NARRATION_SEGMENTS]
        tts_results = await asyncio.gather(*tts_tasks)
    
    # Report results
    print("\n=== Image Results ===")
    for r in image_results:
        status = "✓" if r["success"] else "✗"
        print(f"  {status} {r['id']}: {r['url'] or 'FAILED'}")
    
    print("\n=== TTS Results ===")
    for r in tts_results:
        status = "✓" if r["success"] else "✗"
        print(f"  {status} {r['id']}: {r['file'] or 'FAILED'}")
    
    # Save manifest
    manifest = {
        "images": [{"id": r["id"], "url": r["url"]} for r in image_results],
        "audio": [{"id": r["id"], "file": r["file"]} for r in tts_results],
        "narration": NARRATION_SEGMENTS
    }
    with open(f"{OUTPUT_DIR}/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nManifest saved to {OUTPUT_DIR}/manifest.json")

if __name__ == "__main__":
    asyncio.run(main())
