# Open-source / open-weights stack for self-hosted talking-head restyle (state as of 10 Oct 2026)

> Method note (read first). WebFetch could not resolve any host in this session, so primary facts come from
> shallow `git clone`s of the official GitHub repos (README / LICENSE / CHANGELOG at HEAD as of 2026-10-10) and of
> the `Comfy-Org/docs` + `Comfy-Org/workflow_templates` repos (the source of docs.comfy.org). Hosted-API prices
> come only from web-search snippets (mostly secondary sources) and are flagged as such. Hugging Face model cards
> were NOT readable directly; HF links are given as they appear in the GitHub READMEs.

## Q1. Stage 1 — Which open model best keeps my real performance + lip-sync while changing outfit / background / style at 720p? Max clip length and cross-clip consistency?

### Takeaway
For "same person, same performance, new look" the most production-proven open option is still **Wan2.2-Animate-14B** (Apache-2.0, Sep 2025): *replace/mix* mode keeps the original background and lighting, *animate/move* mode re-renders the person (new outfit/style from an edited reference frame) and takes background from the reference image; it generates 77-frame segments chained with 1 or 5 overlap frames, so length is effectively unlimited but drift/seams accumulate. In 2026 it gained strong open competitors: **Wan-Animate-2** (Aug 2026, Apache-2.0, end-to-end without pose extraction, text-controlled camera, fresh background from prompt, but no replace mode documented), **SCAIL-2** (Zhipu, Jun 2026, Apache-2.0, animation + replacement + relighting LoRA), **Bernini-R** (ByteDance, Jun 2026, Apache-2.0, instruction/ref-guided v2v restyle & editing), **LTX-2.3/2.5 IC-LoRA** v2v (Lightricks, community license, now with chunked long-video and native audio), and **MiniMax-H3 Ref2VA** (Aug 2026, open weights, ≤15 s video editing with native audio, restrictive license). None of them guarantees phoneme-accurate lip-sync, so a lip-sync post-pass (Q3) remains standard.

### Cited Findings
**Wan2.2-Animate-14B (Alibaba Tongyi / HumanAIGC)**
- Released 19 Sep 2025 as "an unified model for character animation and replacement with holistic movement and expression replication"; weights + inference code; Diffusers integration added 13 Nov 2025 (`Wan-AI/Wan2.2-Animate-14B-Diffusers`, `WanAnimatePipeline`) — [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- Preprocessing at `--resolution_area 1280 720`; replacement mode adds `--replace_flag` and `--use_relighting_lora`; animate mode uses `--retarget_flag --use_flux` (FLUX used for pose retargeting edit) — [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- Long video: `segment_frame_length=77` ("clip_len") and `prev_segment_conditioning_frames=1` ("refert_num"); CLI help: "How many frames used for temporal guidance. Recommended to be 1 or 5." — [Wan2.2 GitHub README + generate.py](https://github.com/Wan-Video/Wan2.2)
- Authors advise NOT to use LoRAs trained on Wan2.2 with Wan-Animate ("unexpected behavior") — [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- License: Apache-2.0, "We claim no rights over your generated contents" — [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- Official single-GPU 14B 720p commands are documented as needing ≥80 GB VRAM (with `--offload_model True --convert_model_dtype`); multi-GPU via FSDP + DeepSpeed Ulysses (8 GPUs) — [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- ComfyUI native template `video_wan2_2_14B_animate`: modes "Mix" (replace character, keep video background via `background_video` + `character_mask`) and "Move" (disconnect those inputs); DWPose preprocesses pose + face control videos; Points Editor (KJNodes) for mask; each "Video Extend" group adds 77 frames (~4.8125 s at 16 fps) and must be chained manually (link `batch_images` and `video_frame_offset`); width/height must be multiples of 16 — [ComfyUI docs: Wan2.2 Animate](https://docs.comfy.org/tutorials/video/wan/wan2-2-animate)
- Extra official templates: `template_purz_wan22_animate_auto_character_replace`, `templates_purz_wan22_animate_auto_full_scene` — [Comfy-Org workflow_templates](https://github.com/Comfy-Org/workflow_templates)
- Hosted max length examples: WaveSpeed bills Animate 5–120 s per job — [WaveSpeed blog (es)](https://wavespeed.ai/blog/es/posts/introducing-wavespeed-ai-wan-2-2-animate-on-wavespeedai/); muapi lists "480p or 720p, up to 120 seconds" — [muapi](https://muapi.ai/comparison/wan2.2-animate)

**Wan-Animate-2 (Wan2.2-Animate-2-14B)**
- Released 7 Aug 2026 (inference scripts, Base and Distillation weights); Apache-2.0; arXiv 2608.06009; HF `Wan-AI/Wan2.2-Animate-2-14B`; Diffusers `WanAnimate2Pipeline` (Base 40 steps; Distilled 10 steps, CFG 1.0); DiffSynth-Studio + ComfyUI integration — [Wan-Animate-2 GitHub](https://github.com/Wan-Video/Wan-Animate-2)
- "End-to-end character animation framework that directly consumes driving videos … eliminating intermediate motion extractors"; adds text-driven viewpoint control; a Lite variant for efficiency — [Wan-Animate-2 GitHub](https://github.com/Wan-Video/Wan-Animate-2)
- Defaults tuned for 8× A800 for 720p; 480p tested on 2× A800; prompt must be an LLM caption of the reference (appearance + background, no actions) — [Wan-Animate-2 GitHub](https://github.com/Wan-Video/Wan-Animate-2)
- ComfyUI: "no pose extraction or skeleton preprocessing", "generates a fresh background from your text prompt instead of copying the driving video's background"; ships INT8 convrot / BF16 / distilled variants + LightX2V LoRA (templates `video_wan_animate2`, `video_wan_animate2_distilled`) — [ComfyUI docs: Wan Animate 2](https://docs.comfy.org/tutorials/video/wan/wan-animate-2)
- Announced features: multi-character animation and real-time streaming generation — [Wan on X](https://x.com/Alibaba_Wan/status/2087005664174657566); Lite variant reportedly streams 24 fps at 400×720 — [OpenSourceForU (secondary)](https://www.opensourceforu.com/2026/08/alibaba-open-sources-wan-animate-2/)
- Hosted on KIE.ai as "Wan Animate 2 API" — [kie.ai](https://kie.ai/wan-animate-2)

**SCAIL-2 (Zhipu / zai-org), built on Wan2.1**
- Model + inference code 9 Jun 2026; ComfyUI integration same day; multi-reference 13–17 Jun; relighting LoRA for replacement mode 15 Jul; training code 6 Aug 2026; Apache-2.0 — [SCAIL-2 GitHub](https://github.com/zai-org/SCAIL-2)
- End-to-end driving (no skeleton) trained on 60K synthesized motion pairs (from SCAIL-Preview, Wan-Animate, MoCha) + "Bias-Aware DPO" LoRA; supports 512p and 704p (H, W divisible by 32, e.g. 704×1280) — [SCAIL-2 GitHub](https://github.com/zai-org/SCAIL-2)
- ComfyUI: Animation vs Replacement (`replace_mode`), 81 frames/segment, 5 overlap frames (`previous_frame_count`), segments = ceil(total_frames/76), "WanSCAILToVideo cannot queue all segments automatically. Run each segment manually." — [ComfyUI docs: SCAIL-2](https://docs.comfy.org/tutorials/video/zai/scail2)

**Bernini / Bernini-R (ByteDance)**
- Bernini-R (renderer-only, fine-tuned from Wan) weights 1 Jun 2026; 1.3B variant 9 Jun; full Bernini (MLLM planner + DiT renderer) 11 Jun; Bernini-v2; training code 13 Jul 2026; Apache-2.0; tasks t2i, i2i, t2v, v2v, rv2v, r2v; H100 recommended; authors claim "first tier among leading closed-source commercial models" on video editing (self-built arena) — [Bernini GitHub](https://github.com/bytedance/Bernini)
- ComfyUI native nodes: v2v = "Video-to-video restyling", rv2v = source video + ref images (relighting, subject insertion, multi-piece outfits) — [ComfyUI docs: Bernini-R](https://docs.comfy.org/tutorials/video/bytedance/bernini-r)

**Wan VACE / Wan Fun Control (structure-preserving v2v)**
- Wan2.1-VACE (1.3B 480p; 14B 480p+720p) released 14 May 2025, Apache-2.0 — [Wan2.1 GitHub](https://github.com/Wan-Video/Wan2.1); ComfyUI: VACE-14B ~32 GB file; on RTX 4090 720×1280×81 frames ≈ 40 min, 640×640×49 ≈ 7 min (no distill LoRA) — [ComfyUI docs: VACE](https://docs.comfy.org/tutorials/video/wan/vace)
- Wan2.2-VACE-Fun-A14B (Alibaba PAI, based on Wan2.2-T2V-A14B): Canny/Depth/Pose/MLSD/trajectory + subject reference; 512/768/1024 multi-res, 81 frames at 16 fps; Wan2.2-Fun-A14B-Control similar — [VideoX-Fun GitHub](https://github.com/aigc-apps/VideoX-Fun)

**LTX-2 family (Lightricks; joint audio+video)**
- Current release LTX-2.5 (22B transformer, Gemma-4-12B text encoder bundled; ~66 GiB download for the distilled set; gated HF repo); pipelines: Distilled, DFR (production), ICLoraPipeline ("video-to-video … transformations"), A2Vid (audio-conditioned), Retake (regenerate a time region), DubItPipeline; LTX-2.3 kept as legacy — [LTX-2 GitHub](https://github.com/Lightricks/LTX-2)
- LTX-2.5 support landed in ltx-pipelines 1.2.0 on 11 Aug 2026; 1.4.0 (29 Sep 2026) added `--chunked` long-video on Distilled/TI2Vid/A2Vid/Dub-It/IC-LoRA with default 97-frame windows and 25-frame carry, crossfaded seams, VRAM bounded by window size — [LTX-2 CHANGELOG](https://github.com/Lightricks/LTX-2/blob/main/CHANGELOG.md)
- IC-LoRAs for v2v: LTX-2.3 Union-Control (depth+pose+edges), Motion-Track-Control, Detailer, Pose-Control, HDR, DubIt — [LTX-2 MODELS-LTX-2.3.md](https://github.com/Lightricks/LTX-2/blob/main/MODELS-LTX-2.3.md); ComfyUI also lists LTX-2.3 ID-LoRA ("adapt a person's appearance and voice", `ltx-2.3-id-lora-talkvid-3k`) and IA2V (image+audio → lip-synced video) — [ComfyUI docs: LTX-2.3](https://docs.comfy.org/tutorials/video/ltx/ltx-2-3)
- LTX-2.5 ComfyUI: native 4K HDR, synchronized audio-video up to 50 FPS, auto-duration — [ComfyUI docs: LTX-2.5](https://docs.comfy.org/tutorials/video/ltx/ltx-2-5)

**MiniMax-H3 (open weights, Aug 2026)**
- 33B dense single-stream "Omni Transformer" (≈13B of it in AdaLN branches that can be precomputed), Qwen3-VL-32B encoder, joint video + 32 kHz stereo audio, 4–15 s output, 768p native (2K "Regenerate" module and H3-Context-IR prompt system NOT open, API only); two checkpoints: FL2VA (T2V / first-last frame) and Ref2VA (≤9 images, ≤3 videos of 2–15 s, ≤3 audio clips); README's Ref2VA example is explicitly "video editing" of a source clip (subject retained, mouth re-animated to new dialogue, voice timbre from reference audio); serve via SGLang (4 GPUs in example), vLLM, Diffusers, ComfyUI — [MiniMax-H3 GitHub](https://github.com/MiniMax-AI/MiniMax-H3)
- ComfyUI: native canvas 1344×768; duration grid 17k+5 frames at 24 fps; `MiniMaxH3AddGuide` anchors frames/clips (e.g., first 22 frames of an existing video + audio for continuation) — "Anchoring a guide is not video-to-video" — [ComfyUI docs: H3 native](https://docs.comfy.org/tutorials/video/minimax/minimax-h3-native)
- Wan2GP v17.17 (7 Oct 2026): "15 seconds of H3 video at 1080p … now you just need 11 GB of VRAM", 5–6 GB at 480p (with offloading); also "Viggle Animate", an H3-based Wan-Animate-like model (3 steps) — [Wan2GP GitHub](https://github.com/deepbeepmeep/Wan2GP)
- VideoX-Fun hosts MiniMax-H3 weights + "TaoMate-H3-Adapter" (streaming speech-driven generation, 3-step) — [VideoX-Fun GitHub](https://github.com/aigc-apps/VideoX-Fun)

**HunyuanVideo 1.5 / HunyuanCustom (Tencent)**
- HunyuanVideo-1.5: 8.3B DiT, released 20 Nov 2025; 480p/720p + 1080p SR; min 14 GB VRAM with offload; ComfyUI + Diffusers; step-distilled 480p I2V (Dec 2025) — [HunyuanVideo-1.5 GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5). No v2v editing/replace mode in the README.
- HunyuanCustom (May 2025): text/image/audio/video inputs, "video editing by replacing subjects in the video with those in the provided image", audio-driven; 720×1280×129f needs 80 GB (8 GB via WanGP) — [HunyuanCustom GitHub](https://github.com/Tencent-Hunyuan/HunyuanCustom) (2025, superseded in practice by Wan-based tools)

**UniAnimate-DiT (Apr 2025, superseded)** — pose-driven LoRA on Wan2.1-I2V-14B-720P with long-video mode and TeaCache — [UniAnimate-DiT GitHub](https://github.com/ali-vilab/UniAnimate-DiT)

**Newer open Wan base models?**
- Official Wan-AI weights stop at Wan2.2 (+ Animate-2, Dancer, etc.); Wan 2.6 (16 Dec 2025) is API-only via Alibaba Model Studio — [wan27.org (secondary)](https://wan27.org/blog/wan-2-6-open-source-guide), [Fastlane (secondary)](https://www.usefastlane.ai/models/wan-2-6). Claims of open Wan 2.7 / Wan 3.0 weights conflict and one reviewer calls them SEO fabrications — [localaimaster (secondary)](https://localaimaster.com/blog/wan-2-7-open-source), [wan27.org (secondary)](https://wan27.org/blog/wan-3-open-source). Wan2.5/2.6/2.7 GitHub repos under Wan-Video do not exist (clone failed in this session); KIE.ai sells Wan 2.5/2.6/2.7 as APIs — [kie.ai Wan 2.7](https://kie.ai/wan-2-7-video)

### Inferences
- Best default for a creator's talking head (720p, keep performance, change outfit/era/style): **Wan2.2-Animate in move/animate mode** driven by the real clip + a first frame restyled with an image editor (Q6) — it transfers face expression via face crops and body via pose, and the new background comes from the edited frame. For "keep my room, change only clothes", use **replace/mix mode** (+ relighting LoRA) or SCAIL-2 replacement. Wan-Animate-2 is likely higher fidelity for hands/micro-expressions but (per docs) re-generates background from the prompt and lacks a documented replace mode; test both.
- For pure *style* restyle (anime/oil-paint/era film look) where geometry should be kept, Bernini-R v2v/rv2v, VACE/Fun-Control with depth+pose, or LTX-2.3 Union-Control IC-LoRA are better fits than Animate.
- Cross-clip consistency: all Wan-family tools stitch ~5 s windows (77/81 frames) with 1–5 overlap frames; LTX now does 97-frame windows with 25-frame carry and crossfade. Expect identity/colour drift to grow with segment count; mitigate with the identical reference image for every segment, short shots (cut on camera changes), and a single colour grade in post.
- Lip-sync: these v2v models copy mouth shapes visually from the driving clip; they do not "listen" to audio (except LTX/H3 which generate audio jointly). For tight sync after restyle, run LatentSync / InfiniteTalk-v2v / LTX Dub-It on the restyled output with the original audio.

### Gaps
- No first-party throughput numbers (s/s of video) for Wan-Animate / Animate-2 / SCAIL-2 / Bernini-R at 720p on H100 were found; the Wan2.2 README efficiency table is an image.
- Whether Wan-Animate-2 has a replacement (background-keeping) mode could not be confirmed (README and ComfyUI docs only describe animation).
- No independent benchmark comparing Wan-Animate vs Animate-2 vs SCAIL-2 vs Bernini-R on talking-head lip/teeth fidelity was found; Reddit threads were not reachable via search.

## Q2. Stage 2 — Audio-driven talking avatars (photo/video + audio → talking video): which are best and which handle minutes-long video?

### Takeaway
Minutes-long, open, commercially usable options in Oct 2026: **InfiniteTalk** (Apache-2.0; unlimited streaming, both image-to-video and video-to-video dubbing; colour shift beyond ~1 min in I2V), **LongCat-Video-Avatar 1.5** (MIT, May 2026, Whisper-large-v3 lip-sync, robust long video via continuation, 8-step distill), **Live Avatar** (Apache-2.0, real-time streaming, 10,000+ s, needs 48–80 GB), **StableAvatar** (MIT, infinite length but 1.3B/480p), **SoulX-FlashHead** (Apache-2.0, real-time head-only on a 4090), and **Wan2.2-S2V** (Apache-2.0, clip-chained to audio length). Short-clip (≤15 s) models: MultiTalk, HuMo, OmniAvatar, FantasyTalking, HunyuanVideo-Avatar, EchoMimic V3. Sonic and TalkVerse are non-commercial.

### Cited Findings
- **InfiniteTalk** (MeiGen-AI, 19 Aug 2025): "unlimited-length talking video generation … audio-driven video-to-video and image-to-video"; base Wan2.1-I2V-14B-480P; `--size infinitetalk-480 / -720`; `--mode streaming` for long video; default `--max_frame_num` = 1000 frames (40 s); I2V "good results … up to 1 minute. Beyond 1 minute, color shifts become more pronounced"; V2V "mimics the original video's camera movement, though not identically"; FusionX LoRA "exacerbates color shift over 1 minute and reduces ID preservation"; LightX2V LoRA = 4 steps; fp8/int8 quant, low-VRAM mode `--num_persistent_param_in_dit 0`; ComfyUI via Kijai WanVideoWrapper; Apache-2.0 — [InfiniteTalk GitHub](https://github.com/MeiGen-AI/InfiniteTalk). Official ComfyUI template `video_wan2_1_infinitetalk` — [Comfy-Org workflow_templates](https://github.com/Comfy-Org/workflow_templates)
- **MultiTalk** (May–Jul 2025): multi-person, 480p/720p, "video generation up to 15 seconds"; 480p on a single RTX 4090 in low-VRAM mode — [MultiTalk GitHub](https://github.com/MeiGen-AI/MultiTalk)
- **LongCat-Video-Avatar** (16 Dec 2025) and **1.5** (21 May 2026): single/multi-stream audio; tasks AT2V, ATI2V, video continuation; v1.5 swaps wav2vec2 for Whisper-large-v3 "for more accurate lip synchronization", "robust long-video generation", stylized domains (anime), 8-step distillation (required for v1.5), INT8 DiT; 480p/720p; `--num_segments` for long videos; base LongCat-Video 13.6B "minutes-long videos without color drifting"; MIT license — [LongCat-Video GitHub](https://github.com/meituan-longcat/LongCat-Video)
- **Live Avatar** (Alibaba Quark, Dec 2025; ECCV 2026 spotlight): 14B, "real-time, streaming, infinite-length", 10,000+ s continuous; 45 FPS on multi-H800 with 4-step sampling; single-GPU code needs ≥80 GB; FP8 (v1.1, 20 Jan 2026) enables 48 GB GPUs; Apache-2.0 (Wan base Apache) — [LiveAvatar GitHub](https://github.com/Alibaba-Quark/LiveAvatar)
- **StableAvatar** (Aug 2025; NeurIPS 2026): "infinite-length" end-to-end; base Wan2.1-1.3B, 480×832 / 832×480 / 512×512; overlap window 5–15 frames; ComfyUI by smthemex; MIT — [StableAvatar GitHub](https://github.com/Francis-Rings/StableAvatar)
- **SoulX-FlashHead** (Feb 2026): 1.3B, "Infinite Real-time Streaming Talking Heads"; Lite 96 FPS on one RTX 4090; Pro 10.8 FPS on 4090 or real-time on 2× RTX 5090; ComfyUI node by RunningHub; Apache-2.0 — [SoulX-FlashHead GitHub](https://github.com/Soul-AILab/SoulX-FlashHead)
- **Wan2.2-S2V-14B** (26 Aug 2025): speech-to-video, 480p/720p; clips of 48 or 80 frames chained via `--num_clip` ("the whole video will not exceed the length of audio"); CosyVoice TTS hook; ComfyUI template `video_wan2_2_14B_s2v`; Apache-2.0 — [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- **HuMo** (ByteDance, Sep 2025): 17B and 1.7B (1.7B: 480p in 8 min on a 32 GB GPU); trained on 97 frames at 25 fps, "longer than 97 frames may degrade"; ComfyUI official support; Apache-2.0 — [HuMo GitHub](https://github.com/Phantom-video/HuMo)
- **OmniAvatar** (Jun 2025): 14B, "480p only for now"; A800: 16.0 s/it at 36 GB, 22.1 s/it at 8 GB (offload), 4.8 s/it on 4 GPUs; overlap 1 or 13 frames; Apache-2.0 — [OmniAvatar GitHub](https://github.com/Omni-Avatar/OmniAvatar)
- **FantasyTalking** (Apr 2025): on Wan2.1-I2V-14B-720P; A100 512×512×81: 15.5 s/it at 40 GB, 42.6 s/it at 5 GB; Apache-2.0 — [fantasy-talking GitHub](https://github.com/Fantasy-AMAP/fantasy-talking)
- **EchoMimic V3** (Aug 2025; AAAI 2026): 1.3B; "12G VRAM"; Flash/pro checkpoint 22 Jan 2026; tested A100/4090D/V100; Apache-2.0 — [echomimic_v3 GitHub](https://github.com/antgroup/echomimic_v3)
- **HunyuanVideo-Avatar** (28 May 2025): min 24 GB for 704×768×129f ("very slow"), 96 GB recommended; 10 GB via Wan2GP; Tencent Hunyuan Community License — [HunyuanVideo-Avatar GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-Avatar)
- **Hallo3** (CVPR 2025): derivative of CogVideoX-5B-I2V, must follow CogVideoX license; tested on H100 — [hallo3 GitHub](https://github.com/fudan-generative-vision/hallo3)
- **Sonic** (Tencent, CVPR 2025): CC BY-NC-SA 4.0, "our license is non-commercial" — [Sonic GitHub](https://github.com/jixiaozhong/Sonic)
- **TalkVerse** (Snap, Dec 2025): minute-long generation on Wan2.2-TI2V-5B; Snap Inc. Non-Commercial License — [TalkVerse GitHub](https://github.com/snap-research/TalkVerse)
- **MOVA** (OpenMOSS, Jan 2026): open joint video–audio model claiming SOTA multilingual lip-sync; ComfyUI community node; Apache-2.0 — [MOVA GitHub](https://github.com/OpenMOSS/MOVA)
- **LTX-2.3 IA2V / ID-LoRA**: image + audio → lip-synced video; ID-LoRA adapts appearance and voice — [ComfyUI docs: LTX-2.3](https://docs.comfy.org/tutorials/video/ltx/ltx-2-3)
- Hosted InfiniteTalk advertised up to 10-minute audio at 480p/720p — [Atlas Cloud](https://www.atlascloud.ai/infinitetalk)

### Inferences
- For a creator who films themselves, the audio-driven route is a fallback (e.g., re-dubbing lines or generating B-roll avatars); the primary path is v2v (Q1). InfiniteTalk's *video-to-video* mode is the closest bridge: it keeps the real clip as a "sparse frame" reference and regenerates mouth/head/body for new audio at 720p for arbitrary length.
- For long monologues from a single styled still: LongCat-Video-Avatar-1.5 (MIT, newest, Whisper encoder) is the most promising open candidate; InfiniteTalk I2V needs the "image-to-video by zooming" trick beyond ~1 min.

### Gaps
- No head-to-head 2026 benchmark (Sync-C, FID, identity) between InfiniteTalk, LongCat-Avatar-1.5, Live Avatar and FlashHead was found.
- LongCat-Video-Avatar-1.5 VRAM requirement and whether its HF weights carry a licence different from the MIT repo were not verified.

## Q3. Stage 3 — Lip-sync / dubbing post-pass on existing (restyled) video

### Takeaway
Cheapest and most commercially safe face-only pass: **LatentSync 1.6** (Apache-2.0, 512×512 face crop, 18 GB VRAM) or **MuseTalk 1.5** (MIT, 256×256 face, real-time). Whole-frame re-generation dubbing: **InfiniteTalk v2v** (Apache-2.0) and **LTX Dub-It IC-LoRA** (Lightricks community license, matches identity + lips, now chunked for long video). Wav2Lip is non-commercial. MiniMax H3 Ref2VA can re-animate a mouth to new dialogue in ≤15 s clips.

### Cited Findings
- **LatentSync 1.6** (11 Jun 2025): trained on 512×512 "to mitigate the blurriness problem"; Whisper audio embeddings into a latent-diffusion U-Net; min inference VRAM 8 GB (v1.5) / 18 GB (v1.6); InsightFace affine face alignment; Apache-2.0 — [LatentSync GitHub](https://github.com/bytedance/LatentSync)
- **MuseTalk 1.5** (28 Mar 2025): "real-time high quality lip-syncing", face region 256×256, 30 fps+ on V100; MIT code — [MuseTalk GitHub](https://github.com/TMElyralab/MuseTalk)
- **LTX Dub-It**: "rephrasing while keeping the same speaker identity and matching lip movements to new audio"; distilled checkpoint + single IC-LoRA (`Lightricks/LTX-2.3-22b-IC-LoRA-DubIt`), frame count derived from reference video — [LTX-2 pipelines doc](https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-pipelines/docs/pipelines.md); Dub-It supports `--chunked` long video since 29 Sep 2026; LipDubPipeline removed in favour of DubItPipeline — [LTX-2 CHANGELOG](https://github.com/Lightricks/LTX-2/blob/main/CHANGELOG.md); ComfyUI workflow `LTX-2.3_ICLoRA_DubIt_Two_Stage_Distilled.json` — [ComfyUI-LTXVideo GitHub](https://github.com/Lightricks/ComfyUI-LTXVideo)
- **InfiniteTalk v2v**: unlimited-length dubbing; camera motion only approximately preserved; SDEdit improves camera fidelity but adds colour shift — [InfiniteTalk GitHub](https://github.com/MeiGen-AI/InfiniteTalk)
- Wav2Lip open version "for personal/research/non-commercial use only"; KeySync named as closest LatentSync alternative — [Instavar comparison (secondary)](https://instavar.com/research/ai-video/open-source-lip-sync-models)
- Hosted prices: LatentSync on fal $0.20 for videos up to 40 s then $0.005/s; Sync Lipsync 2.0 on fal $3/min (Pro $5/min) — [fal LatentSync](https://fal.ai/models/fal-ai/latentsync/llms.txt), [fal sync-lipsync v2](https://fal.ai/models/fal-ai/sync-lipsync/v2); InfiniteTalk on WaveSpeed from $0.15/run, 720p $0.30 per 5 s (secondary snippets) — [WaveSpeed InfiniteTalk](https://wavespeed.ai/models/wavespeed-ai/infinitetalk)

### Inferences
- Recommended order: restyle (Q1) → LatentSync 1.6 face pass with the original audio (cheap, preserves restyled frame outside the mouth) → if teeth/blur artifacts are visible on stylized faces, try InfiniteTalk v2v or LTX Dub-It (whole-frame, higher cost, risk of identity/colour drift).
- LatentSync/MuseTalk are trained on real faces; heavily stylized (anime/painting) faces may break face detection — test per style.

### Gaps
- No 2026 successor of LatentSync (e.g. "LatentSync 2") was found in the repo (last commit 20 Jun 2025).
- KeySync licence/VRAM not verified; LTX Dub-It quality on stylized faces not documented.

## Q4. Stage 4 — Expression / performance transfer tools

### Takeaway
LivePortrait remains the fast, widely deployed open option (MIT code, but bundled InsightFace models are non-commercial — use MediaPipe variant). X-Portrait (v1, Apache-2.0) is open; X-Portrait 2 open weights were not found. In 2026 the end-to-end animators (Wan-Animate-2, SCAIL-2) and FantasyPortrait (via Kijai wrapper) largely replace standalone expression-transfer for full-frame work.

### Cited Findings
- LivePortrait: MIT; "portrait video editing (aka v2v)" since 19 Jul 2024; adopted by Kuaishou, Douyin, Jianying, WeChat Channels; LICENSE: "The models of InsightFace are for non-commercial research purposes only" and commercial users must handle that; Kijai's ComfyUI-LivePortraitKJ offers MediaPipe "as an alternative to Insightface" — [LivePortrait GitHub](https://github.com/KwaiVGI/LivePortrait)
- X-Portrait repo contains SIGGRAPH 2024 X-Portrait code under Apache-2.0; no X-Portrait 2 code/weights present — [X-Portrait GitHub](https://github.com/bytedance/X-Portrait)
- Follow-Your-Emoji (SIGGRAPH Asia 2024) + "Faster" variant with Taylor-Interpolated Cache (Apr 2025); no LICENSE file in repo root — [FollowYourEmoji GitHub](https://github.com/mayuelala/FollowYourEmoji)
- Kijai WanVideoWrapper supports FantasyPortrait, FantasyTalking, MultiTalk/InfiniteTalk, HuMo, WanAnimate, Lynx, SCAIL, LongCat-Video, VACE — [ComfyUI-WanVideoWrapper GitHub](https://github.com/kijai/ComfyUI-WanVideoWrapper)
- Wan-Animate-2 removes pose extractors to keep "high-fidelity motion" and identity — [Wan-Animate-2 GitHub](https://github.com/Wan-Video/Wan-Animate-2); SCAIL-2 end-to-end driving bypasses skeleton ambiguity — [SCAIL-2 GitHub](https://github.com/zai-org/SCAIL-2)

### Inferences
- Useful niche: LivePortrait to transfer the creator's real facial performance onto a stylized still (e.g. painted portrait) for close-ups at very low cost, then optional diffusion refinement.

### Gaps
- X-Portrait 2 availability: no open release found (only ByteDance demos known); FollowYourEmoji licence unknown.

## Q5. Stage 5 — Matting / segmentation for background-only replacement

### Takeaway
Commercial-safe stack: **SAM 3 / SAM 3.1** (SAM License, royalty-free incl. commercial, text-prompted video tracking) or **SAM 2.1** (Apache-2.0) for masks + **BiRefNet** (MIT) for per-frame high-res mattes. **MatAnyone / MatAnyone 2** give the best temporally stable human video mattes but are S-Lab non-commercial; **RVM** is GPL-3.0. LTX-2.5 "Alpha Gen" is a new generative matting option.

### Cited Findings
- SAM 3: unified promptable segmentation in images and videos with text or visual prompts; SAM License (last updated 19 Nov 2025) grants "non-exclusive, worldwide, non-transferable and royalty-free limited license" with trade-control/ITAR restrictions; SAM 3.1 "Object Multiplex" released 27 Mar 2026 (faster joint multi-object tracking) — [SAM 3 GitHub](https://github.com/facebookresearch/sam3)
- SAM 2 (Apache-2.0) — [SAM 2 GitHub](https://github.com/facebookresearch/sam2)
- MatAnyone 2: inference/eval code Mar 2026; input = video + first-frame mask (e.g. from SAM2); S-Lab License 1.0 (non-commercial); MatAnyone v1 same license — [MatAnyone2 GitHub](https://github.com/pq-yang/MatAnyone2), [MatAnyone GitHub](https://github.com/pq-yang/MatAnyone)
- BiRefNet: MIT, still updated (Sep 2026) — [BiRefNet GitHub](https://github.com/ZhengPeng7/BiRefNet)
- Robust Video Matting: GPL-3.0, last commit Mar 2023 (superseded) — [RVM GitHub](https://github.com/PeterL1n/RobustVideoMatting)
- Official ComfyUI templates `utility_video_segment_sam3`, `utility_image_segment_sam3`, `utility_birefnet_remove_background` — [Comfy-Org workflow_templates](https://github.com/Comfy-Org/workflow_templates)
- LTX-2.5 Alpha Gen: "extract a soft alpha matte from any video" — [Wan2GP GitHub](https://github.com/deepbeepmeep/Wan2GP); `ltx_pipelines.alpha_gen` added 1 Oct 2026 — [LTX-2 CHANGELOG](https://github.com/Lightricks/LTX-2/blob/main/CHANGELOG.md)

### Inferences
- Background-only swap (keep the real person pixels untouched, so lip-sync is perfect by construction): SAM 3 person mask → BiRefNet/MatAnyone matte → composite over a generated background plate (image or Wan/LTX/H3 video) → relight. This is the safest path when only location must change; outfit change requires generative v2v.

### Gaps
- No quantitative hair/edge temporal-stability comparison of SAM 3 + BiRefNet vs MatAnyone 2 was found.

## Q6. Stage 6 — Open image models for styling the first frame / reference

### Takeaway
For a commercial pipeline: **Qwen-Image-Edit-2511** (Apache-2.0, Dec 2025; multi-image, identity-preserving edits) and **FLUX.2 [klein] 4B** (Apache-2.0, Jan 2026) are the safe choices. FLUX.1 Kontext [dev], FLUX.2 [dev]/[klein 9B] and the new **Qwen-Image-2.1** (Sep 2026) are non-commercial/research licences; HunyuanImage-3.0-Instruct needs ≥8×80 GB and has Tencent territorial limits.

### Cited Findings
- Qwen-Image-Edit-2509 and Qwen-Image-Edit-2511 (23 Dec 2025) and Qwen-Image-2512 (31 Dec 2025) live in the Apache-2.0 Qwen-Image repo; LightX2V 8-step distills for 2511/2512 (6 Jan 2026) — [Qwen-Image GitHub](https://github.com/QwenLM/Qwen-Image), [LightX2V GitHub](https://github.com/ModelTC/LightX2V)
- Qwen-Image-2.0 announced 10 Feb 2026 (blog + Qwen Chat; no weights listed in README) — [Qwen-Image GitHub](https://github.com/QwenLM/Qwen-Image)
- Qwen-Image-2.1 (20 Sep 2026): 7B visual generator, unified generation + editing, up to 10 reference images, identity preservation; Turbo 8-step 9 Oct 2026; Day-0 ComfyUI/Diffusers; licensed under "Qwen RESEARCH LICENSE" ("shall not use the Materials for any commercial purpose without … a separate commercial license") — [Qwen-Image-2 GitHub](https://github.com/QwenLM/Qwen-Image-2)
- FLUX.1 Kontext [dev]: FLUX.1-dev Non-Commercial License — [flux GitHub](https://github.com/black-forest-labs/flux)
- FLUX.2 [dev] 32B (25 Nov 2025) non-commercial; FLUX.2 [klein] 4B and 4B Base (15 Jan 2026) Apache-2.0; klein 9B / 9B-KV non-commercial; all support single- and multi-reference editing — [flux2 GitHub](https://github.com/black-forest-labs/flux2)
- HunyuanImage-3.0-Instruct (26 Jan 2026): editing + multi-image fusion, 80B MoE (13B active), ≥8×80 GB; Tencent Hunyuan Community License (not valid in EU/UK/South Korea) — [HunyuanImage-3.0 GitHub](https://github.com/Tencent-Hunyuan/HunyuanImage-3.0)
- Official ComfyUI templates: `image_qwen_image_edit_2511`, `image_qwen_image_edit_2511_int8`, `image_flux2_klein_image_edit_4b_distilled`, `flux_kontext_dev_basic` — [Comfy-Org workflow_templates](https://github.com/Comfy-Org/workflow_templates)

### Inferences
- Restyle the first frame (outfit/era/background) with Qwen-Image-Edit-2511 using the creator's frame + outfit reference images, then feed it to Wan-Animate (move mode) / Wan-Animate-2 / SCAIL-2 as the reference character image.

### Gaps
- Whether Qwen-Image-2.0 weights were ever published was not confirmed.

## Q7. Stage 7 — Voice (open TTS / cloning) and what MiniMax actually open-sources

### Takeaway
Commercially usable open TTS with cloning: **Fun-CosyVoice 3.0** (Apache-2.0, includes Russian) and **IndexTTS-2/2.5** (bilibili licence: free unless >100M MAU or >RMB 1B revenue; no Russian). F5-TTS weights and Fish Audio S2 are non-commercial; Microsoft pulled VibeVoice-TTS. MiniMax open-sources LLMs (M1 Apache-2.0, M2 MIT, M2.5 modified-MIT, M3) and, since Aug 2026, the **H3 video+audio model**; its Speech (2.6/2.8) and Hailuo video API products are closed.

### Cited Findings
- Fun-CosyVoice3-0.5B-2512 (Dec 2025): 9 languages incl. Russian + 18 Chinese dialects, instruct control of emotion/speed; Apache-2.0 — [CosyVoice GitHub](https://github.com/FunAudioLLM/CosyVoice)
- IndexTTS-2 (8 Sep 2025: emotion control, duration control) and IndexTTS-2.5 (10 Aug 2026: zh/en/ja/es/ar, faster, `duration_factor` 0.5–2.0×); bilibili Model Use License requires a separate licence above 100M MAU or RMB 1B annual revenue and bars using it to improve other (commercial) models — [index-tts GitHub](https://github.com/index-tts/index-tts)
- F5-TTS v1 (Mar 2025): code MIT, pretrained models CC-BY-NC — [F5-TTS GitHub](https://github.com/SWivid/F5-TTS)
- Fish Audio S2 Pro (2026): 80+ languages, 10–30 s reference cloning; Fish Audio Research License — "Any Commercial use … requires a separate license" — [fish-speech GitHub](https://github.com/fishaudio/fish-speech)
- VibeVoice-TTS (90-min, 4 speakers) open-sourced 25 Aug 2025 then code removed 5 Sep 2025 for misuse; Realtime-0.5B (Dec 2025) remains; Microsoft does not recommend commercial use — [VibeVoice GitHub](https://github.com/microsoft/VibeVoice)
- Wan2GP integrates Qwen3 TTS, MiniMax H3 Voice Clone (H3 Ref2VA reused as TTS), Index TTS2/2.5, Chatterbox — [Wan2GP GitHub](https://github.com/deepbeepmeep/Wan2GP)
- MiniMax open weights: MiniMax-M1 456B/45.9B active, Apache-2.0 — [MiniMax-M1 GitHub](https://github.com/MiniMax-AI/MiniMax-M1); MiniMax-M2 230B/10B active, MIT — [MiniMax-M2 GitHub](https://github.com/MiniMax-AI/MiniMax-M2); MiniMax-M2.5 (13 Feb 2026) "MiniMax Model License" (modified MIT, attribution) — [MiniMax-M2.5 GitHub](https://github.com/MiniMax-AI/MiniMax-M2.5); MiniMax-M3 ~428B/23B active, native multimodal, 1M context, licence file on HF — [MiniMax-M3 GitHub](https://github.com/MiniMax-AI/MiniMax-M3); MiniMax-H3 video model, MiniMax H3 Community License — [MiniMax-H3 GitHub](https://github.com/MiniMax-AI/MiniMax-H3)
- MiniMax H3 weights went public ~3 Aug 2026 (HF `MiniMaxAI/MiniMax-H3`, ComfyUI mirror `Comfy-Org/MiniMax-H3`) — [ComfyUI Wiki news](https://comfyui-wiki.com/en/news/2026-08-03-minimax-h3-open-weights-comfyui)
- MiniMax Speech 2.6 is closed/API-only — [DataLearner (secondary)](https://www.datalearner.com/ai-models/pretrained-models/minimax-speech-2-6); Speech 2.8 HD/Turbo (16 Jul 2026) listed as hosted API — [OpenRouter](https://openrouter.ai/minimax/speech-2.8-hd-20260716); H3's own API at platform.minimax.io and app at hailuoai.video — [MiniMax-H3 GitHub](https://github.com/MiniMax-AI/MiniMax-H3)

### Inferences
- For Russian-language re-dubbing, Fun-CosyVoice 3 is the only clearly commercial-safe open option verified here; MiniMax's best voice tech (Speech 2.x) must be used via API.

### Gaps
- Qwen3-TTS, Chatterbox, Omnivoice licences and Russian quality were not verified. MiniMax-01 / M2.1 licences not re-checked this session.

## Q8. Stage 8 — Orchestration, hosting, GPU sizing, speed and cost per finished minute

### Takeaway
ComfyUI (official templates exist for Wan2.2 Animate, Wan Animate 2, SCAIL-2, InfiniteTalk, S2V, VACE v2v, Bernini-R, LTX-2.3/2.5 IC-LoRA, MiniMax H3, SAM 3, BiRefNet, Qwen-Image-Edit-2511) driven headless via comfy-cli or the server API is the practical backbone; Wan2GP is the low-VRAM alternative. 14B Wan-family models at 720p want 48–80 GB (H100/A100/L40S-48GB/RTX 6000 Pro) for comfort; 24–32 GB cards work with fp8/int8 + offload + 4-step LoRAs. Hosted Wan-Animate 720p ≈ $0.08/s (WaveSpeed) → ≈ $4.8 per finished minute; self-hosted on a rented H100 is plausibly ~$1–3/min (estimate).

### Cited Findings
- comfy-cli: `comfy install`, custom-node and model management, "Run workflows against a local ComfyUI server, including auto-conversion of UI-format JSON", or route to Comfy Cloud with `comfy run --workflow ./workflow.json --where cloud` (async `prompt_id`, `--wait`) — [comfy-cli GitHub](https://github.com/Comfy-Org/comfy-cli)
- Official template list (relevant): `video_wan2_2_14B_animate`, `template_purz_wan22_animate_auto_character_replace`, `video_wan_animate2(_distilled)`, `video_wan21_scail2_character_replacement(_int8)`, `video_wan2_1_infinitetalk`, `video_wan2_2_14B_s2v`, `video_humo`, `video_wan_vace_14B_v2v`, `video_bernini_r_video_editing`, `video_ltx2_3_ic_lora`, `video_ltx2_3_id_lora`, `video_ltx2_3_ia2v`, `video_minimax_h3_r2v`, `utility_video_segment_sam3`, `utility_birefnet_remove_background`, `image_qwen_image_edit_2511`, plus API nodes `api_sync_so_lip_sync_video` — [Comfy-Org workflow_templates](https://github.com/Comfy-Org/workflow_templates)
- Kijai WanVideoWrapper: frontline Wan features (context windows, block swap) — [ComfyUI-WanVideoWrapper GitHub](https://github.com/kijai/ComfyUI-WanVideoWrapper); Wan2GP: "as little as 6 GB of VRAM", supports Wan 2.1/2.2, MiniMax H3, LTX-2/2.3/2.5, Hunyuan 1.5, LongCat — [Wan2GP GitHub](https://github.com/deepbeepmeep/Wan2GP)
- LightX2V speed (Wan2.1-I2V-14B-480P, 40 steps, 81 frames): single H100 5.18 s/it (Diffusers 9.77 s/it); 8×H100 0.75 s/it; single RTX 4090D 20.26 s/it; 4-step distilled LoRAs for Wan2.1/2.2, Wan2.2 I2V 4-step 720p (Apr 2026), NVFP4 Blackwell variants, MiniMax-H3 Turbo 4/8-step LoRAs (Aug 2026) — [LightX2V GitHub](https://github.com/ModelTC/LightX2V)
- VACE-14B on RTX 4090: 720×1280×81 frames ≈ 40 min — [ComfyUI docs: VACE](https://docs.comfy.org/tutorials/video/wan/vace)
- KIE.ai hosts Wan 2.2 Animate as `wan/2-2-animate-move` and `wan/2-2-animate-replace` (video URL + image URL + resolution; bearer token) — [docs.kie.ai Animate Replace](https://docs.kie.ai/market/wan/2-2-animate-replace), [docs.kie.ai Animate Move](https://docs.kie.ai/market/wan/2-2-animate-move); also Wan Animate 2 — [kie.ai](https://kie.ai/wan-animate-2) and Wan 2.2 speech-to-video turbo — [kie.ai](https://kie.ai/wan-speech-to-video-turbo). Price not found on kie.ai pages in search; a third-party reseller lists animate-replace at 7/12/15 credits per second for 480p/580p/720p — [Vidgo (secondary)](https://vidgo.ai/apis/models/wan-animate); kie credits ≈ $0.005 each per a third party — [CometAPI (secondary)](https://www.cometapi.com/fr/vs/kie-ai/). KIE InfiniteTalk availability only via a promotional article — [BreakingAC (promotional)](https://breakingac.com/news/2025/dec/05/how-to-choose-the-most-cost-effective-infinite-talk-api-the-efficient-solution-provided-by-kieai/)
- WaveSpeed Wan 2.2 Animate: 480p $0.20 / 5 s, 720p $0.40 / 5 s, 5 s minimum, max 120 s billing; 30 s at 720p = $2.40 — [WaveSpeed blog (es)](https://wavespeed.ai/blog/es/posts/introducing-wavespeed-ai-wan-2-2-animate-on-wavespeedai/), [aireiter guide](https://aireiter.com/blog/wan2-2-animate-guide)
- fal / Replicate Wan-Animate price: only third-party estimates (~$0.50/generation) — [muapi (estimate)](https://muapi.ai/comparison/wan2.2-animate); fal hosts MiniMax H3 incl. LoRA endpoint — [fal H3](https://fal.ai/models/minimax/h3/text-to-video/lora)
- RunPod (Jul–Aug 2026): A100 80GB $1.19/h, RTX 5090 $0.69/h, L40S $0.79/h, H100 80GB from $1.99/h (official page); a review lists H100 PCIe $2.89/h, A100 $1.39/h (Secure Cloud) — [RunPod pricing](https://www.runpod.io/gpu-cloud/pricing), [Hackceleration review](https://www.hackceleration.com/labs/runpod-pricing), [ComputePrices](https://computeprices.com/providers/runpod/gpus/rtx5090)
- Third-party estimates for Wan 2.x 14B at 720p on H100 conflict (≈10–12 min per 5 s vs ≈45–60 s at 40 steps) — [Spheron guide](https://www.spheron.network/blog/ai-video-generation-gpu-guide/)

### Inferences
- GPU sizing: 24 GB (4090) = 480p comfortable, 720p only with fp8/int8 + block-swap/offload and slow; 32 GB (5090) = workable 720p with LightX2V 4–6-step LoRAs; 48 GB (L40S/RTX 6000-class, LiveAvatar FP8) = comfortable; 80 GB (A100/H100) = official single-GPU 720p settings for Wan 14B, Live Avatar and LTX-2.5 DFR.
- Speed estimate (derived, not measured): 480p 81-frame Wan-14B step ≈5 s on H100 → 4–6 distilled steps ≈ 30–60 s per 5 s clip incl. encode/decode; 720p ≈ 2.25× tokens → roughly 1.5–4 min per 5 s segment, i.e. ~20–50 s of GPU per second of 720p video → ~20–50 min H100 per finished minute → ~$1–2.5/min at $2–3/h, before retries and the lip-sync pass (LatentSync adds little).
- Hosted vs self-hosted: WaveSpeed ≈ $4.8/min (720p Animate) + LatentSync on fal ≈ $0.3/min; self-hosting pays off only with steady volume and when running models hosts don't offer (SCAIL-2, Bernini-R, LTX Dub-It long-form).

### Gaps
- No first-party s-per-s benchmarks for Wan-Animate / InfiniteTalk at 720p; KIE.ai official prices not retrieved (kie.ai pages not fetchable this session); fal/Replicate official prices for Animate/InfiniteTalk not confirmed; Modal pricing not researched.

## Q9. Licences — is commercial use allowed?

### Takeaway
Apache-2.0/MIT core (commercial OK): Wan2.1/2.2 incl. Animate, S2V, VACE, Wan-Animate-2, Wan-Dancer, VideoX-Fun Wan2.2-Fun/VACE-Fun (repo Apache-2.0; HF weight cards not checked), SCAIL-2, Bernini, InfiniteTalk, MultiTalk, LongCat-Video(-Avatar), Live Avatar, StableAvatar, SoulX-FlashHead, EchoMimicV3, OmniAvatar, FantasyTalking, HuMo, MOVA, LatentSync, MuseTalk (code), LivePortrait (code), SAM 2, BiRefNet, Qwen-Image-Edit-2509/2511, FLUX.2 klein 4B, CosyVoice. Conditional: LTX-2.x (free < $10M revenue), Tencent Hunyuan (not EU/UK/KR; >100M MAU needs licence), MiniMax H3 (reported < $20M revenue, excludes US/EU/UK/KR; Comfy says commercial use of local outputs needs a paid licence), IndexTTS (>100M MAU / RMB 1B), SAM 3 (royalty-free, trade-control limits). Non-commercial: Sonic, TalkVerse, MatAnyone 1/2, F5-TTS weights, Fish Audio S2, FLUX.1 Kontext dev, FLUX.2 dev/klein 9B, Qwen-Image-2.1, Wav2Lip, InsightFace models; RVM is GPL-3.0.

### Cited Findings
- Wan2.2 Apache-2.0 — [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2); Wan-Animate-2 Apache-2.0 — [GitHub](https://github.com/Wan-Video/Wan-Animate-2); Wan Dancer Apache-2.0 — [ComfyUI docs: Wan Dancer](https://docs.comfy.org/tutorials/video/wan/wan-dancer); SCAIL-2 Apache-2.0 — [GitHub](https://github.com/zai-org/SCAIL-2); Bernini Apache-2.0 — [GitHub](https://github.com/bytedance/Bernini); InfiniteTalk Apache-2.0 — [GitHub](https://github.com/MeiGen-AI/InfiniteTalk); LongCat-Video MIT — [GitHub](https://github.com/meituan-longcat/LongCat-Video); Live Avatar Apache-2.0 — [GitHub](https://github.com/Alibaba-Quark/LiveAvatar)
- LTX-2.x Community License (11 Aug 2026; applies to LTX-2.5+): entities with ≥ $10,000,000 annual revenue (aggregated with affiliates) need a paid Commercial Use Agreement; non-commercial carve-out excludes any revenue-generating or end-user-facing use and training for commercial use; breach → pay standard licence fees; LTX-2 licence (5 Jan 2026) covers LTX-2/2.3 — [LTX-2 LICENSE](https://github.com/Lightricks/LTX-2/blob/main/LICENSE), [LICENSE-2_x](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x), [ltx.io licence page](https://ltx.io/model/license); an additional restriction on building products competing with Lightricks is reported — [ScanCode LicenseDB](https://scancode-licensedb.aboutcode.org/ltx-2-cla-2026.html)
- Tencent Hunyuan Community License (HunyuanVideo 1.5, HunyuanVideo-Avatar, HunyuanCustom, HunyuanImage 3.0): "DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA"; licensees with >100M MAU must request a licence — [HunyuanVideo-1.5 LICENSE](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/LICENSE)
- MiniMax H3: "MiniMax H3 Community License Agreement" (text on HF) — [MiniMax-H3 GitHub](https://github.com/MiniMax-AI/MiniMax-H3); ComfyUI: "Commercial use of locally generated outputs requires a MiniMax commercial license, available through Comfy, the only official reseller. Generations on Comfy Cloud already include commercial rights." — [ComfyUI docs: MiniMax H3](https://docs.comfy.org/tutorials/video/minimax/minimax-h3); third-party summaries: territory excludes EU, UK, South Korea and US; free commercial use under $20M revenue — [Atlas Cloud (secondary)](https://www.atlascloud.ai/hi/blog/guides/minimax-h3-commercial-use-license), [DEV Community (secondary)](https://dev.to/breachprotocol/minimax-shipped-h3s-weights-and-kept-the-best-part-hosted-2aag) — these two descriptions conflict with each other on whether free commercial output use exists.
- Sonic CC BY-NC-SA 4.0 — [GitHub](https://github.com/jixiaozhong/Sonic); TalkVerse Snap Non-Commercial — [GitHub](https://github.com/snap-research/TalkVerse); MatAnyone/MatAnyone2 S-Lab non-commercial — [GitHub](https://github.com/pq-yang/MatAnyone2); RVM GPL-3.0 — [GitHub](https://github.com/PeterL1n/RobustVideoMatting); LivePortrait InsightFace models non-commercial — [GitHub](https://github.com/KwaiVGI/LivePortrait); Hallo3 bound by CogVideoX-5B licence — [GitHub](https://github.com/fudan-generative-vision/hallo3)
- FLUX / Qwen / TTS licences: see Q6 and Q7 sources ([flux2](https://github.com/black-forest-labs/flux2), [Qwen-Image](https://github.com/QwenLM/Qwen-Image), [Qwen-Image-2](https://github.com/QwenLM/Qwen-Image-2), [CosyVoice](https://github.com/FunAudioLLM/CosyVoice), [index-tts](https://github.com/index-tts/index-tts), [fish-speech](https://github.com/fishaudio/fish-speech), [F5-TTS](https://github.com/SWivid/F5-TTS))

### Inferences
- A fully commercial-clean "open" pipeline is possible today: Qwen-Image-Edit-2511 or FLUX.2-klein-4B → Wan2.2-Animate / Wan-Animate-2 / SCAIL-2 → LatentSync 1.6 → SAM 3/BiRefNet → CosyVoice 3, orchestrated in ComfyUI. If the user is in the EU/UK/KR, avoid Tencent Hunyuan and self-hosted MiniMax H3. LTX-2.x is free for a solo creator/startup under $10M revenue.
- Apache-2.0 weights trained on Wan inherit Wan's Apache terms, but auxiliary preprocessors (DWPose, InsightFace, face parsers) carry their own licences — audit each ComfyUI node.

### Gaps
- Full text of the MiniMax H3 Community License (HF) not read; exact territorial/revenue terms are from secondary sources. UniAnimate-DiT and FollowYourEmoji repos have no LICENSE file at root.

## Q10. Known limitations: teeth/mouth artifacts, identity drift, flicker, hands, colour shift

### Takeaway
The recurring failure modes are (1) colour/brightness drift across chained segments (InfiniteTalk >1 min, FusionX LoRA, SDEdit), (2) identity softening on long shots and head turns, (3) imprecise lip shapes in pure v2v restyle (needs lip-sync pass), (4) mouth/teeth blur in face-crop lip-sync (LatentSync 1.6 trained at 512 to reduce it), (5) seams at segment boundaries and manual segment chaining in ComfyUI, (6) degradation past training length (HuMo >97 frames, MultiTalk 15 s), (7) repeated actions in avatar models (LongCat), (8) reference-adherence loss with few-step distills (H3 at 4 steps).

### Cited Findings
- InfiniteTalk: colour shift beyond 1 min in I2V; FusionX LoRA "exacerbates color shift over 1 minute and reduces ID preservation"; V2V camera only approximately followed; SDEdit "introduces color shift" — [InfiniteTalk GitHub](https://github.com/MeiGen-AI/InfiniteTalk)
- OmniAvatar: larger overlap (13 frames) is more coherent "but error propagation is more severe" — [OmniAvatar GitHub](https://github.com/Omni-Avatar/OmniAvatar)
- HuMo: generating longer than 97 frames may degrade performance — [HuMo GitHub](https://github.com/Phantom-video/HuMo); MultiTalk limited to 15 s — [MultiTalk GitHub](https://github.com/MeiGen-AI/MultiTalk)
- LongCat-Video-Avatar: tune `--ref_img_index` / `--mask_frame_range` to "mitigate repeated actions"; large values "may introduce artifacts" — [LongCat-Video GitHub](https://github.com/meituan-longcat/LongCat-Video)
- LatentSync 1.6 exists "to mitigate the blurriness problem" of 256-px training — [LatentSync GitHub](https://github.com/bytedance/LatentSync)
- SCAIL-2: without a correct mask, animation mode "collapse[s] into Replacement-Mode behavior"; segments must be run manually in ComfyUI — [SCAIL-2 GitHub](https://github.com/zai-org/SCAIL-2), [ComfyUI docs: SCAIL-2](https://docs.comfy.org/tutorials/video/zai/scail2)
- Wan-Animate: don't stack Wan2.2 LoRAs — [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2); community guides: block-swap "can reduce identity drift on long shots", use a sharp front-facing reference lit like the source "to reduce color and shading drift", "lip sync isn't always precise" so pair with a lip-sync tool, drift increases when the head turns away, use the identical reference across clips, grade all clips uniformly — [RunComfy guide (secondary)](https://www.runcomfy.com/comfyui-workflows/wan-2-2-animate-swap-characters-lip-sync-workflow-comfyui), [wan-animate.com guide (secondary)](https://wan-animate.com/posts/wan-2-2-animate-motion-types-style-consistency-guide)
- Wan-Animate-2 claims removing pose extractors reduces identity drift and preserves hands/micro-expressions — [OpenSourceForU (secondary)](https://www.opensourceforu.com/2026/08/alibaba-open-sources-wan-animate-2/)
- MiniMax H3: at 4 steps "a reference can end up barely applied, and a subject's pose or face angle can drift"; frames above ~1 MP "do not hold detail" — [ComfyUI docs: MiniMax H3](https://docs.comfy.org/tutorials/video/minimax/minimax-h3)
- LTX chunked generation crossfades seams (default blend = full 25-frame carry) and fixes audio clicks at window seams — [LTX-2 CHANGELOG](https://github.com/Lightricks/LTX-2/blob/main/CHANGELOG.md)
- Lip-sync reviewers: identity drift and mouth artefacting around the 30-second mark are common; Hallo3 targets that — [Instavar (secondary)](https://instavar.com/research/ai-video/open-source-lip-sync-models)

### Inferences
- Plan the edit around ~5–15 s shots (natural for short-form), regenerate per shot with the same styled reference and seed policy, do a single colour grade at the end, and keep an untouched-person fallback (matting + background swap) for shots where face fidelity matters most.

### Gaps
- No quantitative data on hand artefacts or teeth artefacts per model; firsthand Reddit reports could not be retrieved.
