# ByteDance Seedance 2.0 / 2.5 (+ Dreamina/Jimeng, CapCut, OmniHuman) for the "AI avatar talking head" restyle trend — state as of 10 Oct 2026

> Method note (applies to every section): the egress proxy in this session blocked direct page fetches (seed.bytedance.com, docs.kie.ai, fal.ai, wikipedia all refused), so every finding below comes from search-engine extracts of the cited pages, not from reading the full pages. Treat exact numbers as "as quoted in the extract"; where official and third-party sources disagree it is flagged. "Official" = ByteDance Seed / BytePlus / CapCut / Volcengine pages; everything else is third-party (aggregators, resellers, blogs, creators).

## 1. Seedance 2.0 input modes and hard limits (references, input/output length, resolution, aspect ratios, audio, edit/extend)

### Takeaway
Seedance 2.0 (official launch 12 Feb 2026) is a unified audio+video model that takes text plus up to 9 images, 3 video clips and 3 audio clips (12 files total) and outputs 4–15 s clips per generation with native, jointly generated audio. Reference video and reference audio are each capped at 15 s combined. It officially supports video extension and editing. Output resolution started at 480p/720p; 1080p (and on some hosts "4K") was added later. The Fast variant tops out at 720p.

### Cited Findings
- Official launch blog dated **12 Feb 2026**. Inputs: "up to 9 images, 3 video clips, 3 audio clips, plus natural language instructions" at the same time. Output: "15-second high-quality multi-shot audio-video output" with dual-channel audio. It "supports stable and controllable video extension and editing." — [ByteDance Seed, Seedance 2.0 Official Launch](https://seed.bytedance.com/en/blog/official-launch-of-seedance-2-0) (other sites give 7 Feb or 9 Feb for the first Dreamina/Jimeng preview: [seedance2pro timeline](https://seedance2pro.io/blog/seedance-2-release-date-guide))
- Reference counts per type are 9 images / 3 videos / 3 audio, **12 files max total**. ByteDance reportedly recommends using far fewer than the maximum. — [Magic Hour, ModelArk-based reference guide](https://magichour.ai/blog/seedance-20-reference-guide)
- Reference video on ModelArk: each clip **2–15 s**, MP4 or MOV, **≤200 MB** each, 24–60 fps, **combined ≤15 s**. Reference audio: MP3/WAV, ≤15 MB each, **combined ≤15 s**. **Audio cannot be the only reference.** At least one image or video reference must be present. — [Magic Hour](https://magichour.ai/blog/seedance-20-reference-guide). Other hosts cap reference video at 50 MB: [KIE docs, Seedance 2.0](https://docs.kie.ai/market/bytedance/seedance-2) (MP4/QuickTime/Matroska, 50 MB, max 3 files); [Pixazo](https://www.pixazo.ai/models/seedance) is internally inconsistent (200 MB in the table, 50 MB in the prose).
- Output duration: **4–15 s** plus "auto" ([Artlist help](https://help.artlist.io/hc/en-us/articles/35245474706333-Seedance-2-0)). Some hosts expose only discrete values 4/5/6/8/10/12/15 ([Segmind](https://blog.segmind.com/seedance-2-0-release-date-pricing-key-features-for-developers/)).
- Aspect ratios: 21:9, 16:9, 4:3, 1:1, 3:4, 9:16, plus auto/adaptive. — [Runflow](https://www.runflow.io/models/bytedance/seedance-2.0/text-to-video); [Segmind](https://blog.segmind.com/seedance-2-0-release-date-pricing-key-features-for-developers/)
- Resolution:
  - ByteDance's paper, as summarized by a third party, says native output is 480p and 720p ([Magic Hour best-settings](https://magichour.ai/blog/seedance-20-best-settings)).
  - Standard now goes up to 1080p and Fast is capped at 720p. A newer "4K" tier is also mentioned ([Artlist one-pager](https://help.artlist.io/hc/en-us/articles/37430797266973-Seedance-2-0-Family); [Flixier](https://flixier.com/announcements/seedance-2)).
  - BytePlus price lists contain separate 1080p tiers for 2.0, which confirms 1080p on the official API ([framesurfer](https://framesurfer.com/blogs/seedance-2-0-pricing)).
  - KIE accepts `resolution` values 480p/720p/1080p/4k ([kie.ai Seedance 2.0](https://kie.ai/seedance-2-0)). The highest tier is encoded as H.265/HEVC ([vas.mintlify KIE skill](https://vas.mintlify.app/skills/create-video-seedance-2-0)).
- Audio: native joint audio generation is **on by default** on fal and Artlist ([fal guide](https://fal.ai/learn/tools/how-to-use-seedance-2-0); [Artlist](https://help.artlist.io/hc/en-us/articles/35245474706333-Seedance-2-0)). On KIE, `generate_audio` defaults to true ([vas.mintlify](https://vas.mintlify.app/skills/create-video-seedance-2-0)). Leonardo's equivalent flag `motion_has_audio` defaults to false ([Leonardo docs](https://docs.leonardo.ai/v1.0/docs/seedance-20)).
- Mode exclusivity: KIE's 2.0 Mini docs say "Do not combine first_frame_url / last_frame_url with any reference_* field", but KIE's 2.0 example mixes them. The docs are inconsistent. — [KIE Seedance 2.0 Mini docs](https://docs.kie.ai/market/bytedance/seedance-2-mini); [KIE Seedance 2.0 docs](https://docs.kie.ai/market/bytedance/seedance-2)
- Variants in the 2.0 family: Seedance 2.0 (standard), 2.0 Fast (≤720p, cheaper) and 2.0 Mini. — [KIE docs: Fast](https://docs.kie.ai/market/bytedance/seedance-2-fast), [Mini](https://docs.kie.ai/market/bytedance/seedance-2-mini); [Artlist family page](https://help.artlist.io/hc/en-us/articles/37430797266973-Seedance-2-0-Family)
- Editing/extension on hosts:
  - WaveSpeed exposes a dedicated `seedance-2.0/video-edit` endpoint. Its example prompt is "Replace the woman on the right with the person in @image1", and it lists clothing and background swaps as use cases ([WaveSpeed video-edit](https://wavespeed.ai/models/bytedance/seedance-2.0/video-edit)).
  - The extension prompt pattern is "Extend @Video1 by 5 seconds" ([WaveSpeed guide](https://wavespeed.ai/blog/posts/seedance-2-0-complete-guide-multimodal-video-creation/)).
  - Replicate's listing says that a reference video plus text can replace an object, change the background or alter the style "while keeping the original motion and camera work" ([Replicate](https://replicate.com/bytedance/seedance-2.0)).

### Inferences
- For a phone-filmed talking head, the binding constraint is the **15 s total reference-video cap** on 2.0. That is also the output cap. A 3–5 min monologue therefore needs about 12–20 separate generations on 2.0 (or about 6–10 on 2.5, see §4), with stitching in an editor.
- Because 1080p and 4K were added after launch and differ by host, check the `resolution` enum on the chosen host before planning a 1080p vertical (9:16) pipeline. Fast is not an option above 720p.

### Gaps
- I could not open the full official launch page or the ModelArk API reference, so the exact official per-file limits (200 MB vs 50 MB) and the exact date 1080p arrived on 2.0 are unconfirmed.
- I found no official statement of the maximum *input* video resolution or whether input fps/resolution affects output.

## 2. Can it restyle an uploaded real talking-head video (keep motion + lip sync, change outfit/background/style)? Does it keep the original audio?

### Takeaway
Partly. Seedance 2.0 can take your filmed clip as a **reference video** and regenerate a new clip that follows its motion, framing and timing while you change outfit, background or style by prompt plus reference image. It is a **full regeneration, not a pixel-preserving filter**. Lip movement is re-synthesized from audio, not copied frame-accurately from your footage. Output audio is **regenerated**: you can feed your own audio as a reference and it will be close, but not bit-identical. Creators therefore re-lay the original audio in post. On top of this, the real-face block (§3) means your own face is rejected as a reference on most channels unless you go through a verified-likeness flow.

### Cited Findings
- Replicate describes the reference-video mode as able to "replace an object, change a background, or alter style while keeping the original motion and camera work." — [Replicate, bytedance/seedance-2.0](https://replicate.com/bytedance/seedance-2.0)
- Third-party reviews list outfit change and background replacement as in-video editing features. — [PixVerse review](https://pixverse.ai/en/blog/seedance-2-0-review-prompts-and-use-cases); [OpusClip guide](https://www.opus.pro/blog/extend-edit-existing-videos-seedance) (character swap keeps "background, lighting, and timing"; extensions up to 15 s)
- Guides warn that using the wrong mode (reference vs edit vs extend) can make a wardrobe change produce "a new character or room". They recommend changing one element at a time and stating what must stay fixed. — [Artflo (2.5)](https://artflo.ai/blog/seedance-2-5-video-editing-extension-prompts); [PromeAI](https://www.promeai.pro/blog/seedance-2-0-video-editing-extend-replace/)
- Uploaded audio acts as a **structural reference** (rhythm, timing, lip-sync alignment). It is "not a voice cloning or voice replacement tool", so getting an exact line in an exact voice needs a post-production step. — [seedance2pro sound guide](https://www.seedance2pro.net/blog/seedance-2-sound-guide)
- One reference guide shows a pattern where audio from @Video1 drives a character from an image while the outfit and background change. It notes that the output audio "is not 100% identical to the input audio." — [seegen.ai audio guide](https://seegen.ai/seedance-2-0-audio-guide) (from search extract; attribution among results in that query not 100% certain)
- Creator report (May 2026): Seedance 2.0 sometimes failed to lip-sync to the reference and "would change the lyrics". A reference video longer than about **13 s** could break lip-sync, so the creator recommends shorter, whole-second clips. — [Abdullah Yahya blog, May 2026](https://abdullahyahya.com/2026/05/make-realistic-lip-sync-music-videos-with-seedance-2-0/) (creator claim)
- Guides say tight word-level lip-sync to a specific script or track "still needs review". When it fails, they suggest a dedicated lip-sync tool. — [sagnikbhattacharya talking-head guide](https://sagnikbhattacharya.com/blog/seedance-2-lip-sync-talking-head)
- Prompt pattern recommended for talking clips from a reference video: tell Seedance to follow the uploaded audio for lip-sync and preserve character, motion style and camera framing. Use front-facing or slight three-quarter framing, and do not cover the mouth. — [seedance-2.app lip-sync blog](https://seedance-2.app/blog/seedance-2-0-lip-sync); [videoai.me dialogue guide](https://videoai.me/blog/seedance-2-0-dialogue)
- Official framing: 2.0 "supports stable and controllable video extension and editing" ([ByteDance Seed launch](https://seed.bytedance.com/en/blog/official-launch-of-seedance-2-0)). For 2.5, BytePlus says users can refine generated videos "by replacing products, styles, faces, lighting, or backgrounds" ([BytePlus Seedance product page](https://www.byteplus.com/en/product/seedance)) and supports "secondary edits" of specific timestamps or characters ([BytePlus blog, Seedance 2.5](https://www.byteplus.com/en/blog/dreamina-seedance2-5)).

### Inferences
- A workable recipe under current constraints (inference, not a documented ByteDance workflow):
  1. Cut the take into segments of 13–15 s or less.
  2. For each segment, pass `reference_video` = your segment, `reference_image` = the target look, and `reference_audio` = the extracted original audio.
  3. Prompt: "keep performance/framing of @Video1, lip-sync to @Audio1, change outfit/background to …".
  4. In the editor, replace the generated audio with the original track.
  The target-look image must be an AI-generated or verified-asset face, not a raw photo of you (see §3).
- Expect "close but not exact" mouth shapes. Because the lips are regenerated, sync errors show up most on plosives and fast speech. A post-pass lip-sync tool (or OmniHuman, see §6) may still be needed.
- No source shows a frame-accurate preservation guarantee. Seedance is a "reference-to-video" model, not a dedicated v2v style-transfer or face-preserving model.

### Gaps
- I found **no rigorous side-by-side test** of restyling one's own talking-head footage with Seedance 2.0 that measures lip-sync or identity preservation. The evidence is guide or prompt examples plus one creator blog.
- Not found: whether the edit endpoint (WaveSpeed `video-edit`, ModelArk equivalent) can pass the source audio through unchanged when `generate_audio=false`. It is untested in any source I found.
- No Reddit/X creator thread demonstrating the exact "film yourself → restyle era/costume keeping speech" workflow turned up in searches.

## 3. Real-face / real-person restrictions: history (Feb–Apr 2026), current policy, and differences between Jimeng (CN), Dreamina/CapCut (intl) and the API (Volcengine Ark / BytePlus ModelArk)

### Takeaway
Since **9–10 Feb 2026** ByteDance has blocked **direct upload of real human faces** (images or videos) as references for Seedance 2.0. The same applies to 2.5. The photo→personal-voice feature was suspended at the same time. As of Oct 2026 the block is still the documented policy on all first-party channels. The only sanctioned routes are verified-likeness flows:
- **Jimeng/Doubao apps (CN):** liveness verification to create a "digital avatar" (数字分身) of yourself.
- **Volcengine Ark / BytePlus ModelArk (API):** real-person verification plus likeness authorization in the console, or an asset library (asset IDs / Group IDs), for vetted clients.
- **Dreamina international and CapCut:** no self-verification route found; real faces are rejected outright.
Some third-party resellers claim to accept real faces without verification, but this is unverified and contradicts upstream policy.

### Cited Findings
- **9 Feb 2026:** Jimeng operators told creator groups that Seedance 2.0 temporarily no longer supports real-person images or videos as the subject reference. — [Beijing News (新京报)](https://www.bjnews.com.cn/detail/1770694532129745.html); [Tencent News](https://news.qq.com/rain/a/20260210A02B8B00); [CLS (财联社)](https://www.cls.cn/detail/2285598)
- **10 Feb 2026:** ByteDance suspended the Seedance 2.0 feature that generated a personal voice from a face photo. MediaStorm founder Pan Tianhong showed that his photo alone produced near-identical audio of his voice. Jimeng said it would stop allowing real-looking people as reference subjects, and Jimeng and Doubao added live verification where users record their own image and voice. — [TechNode, 10 Feb 2026](https://technode.com/2026/02/10/bytedance-suspends-seedance-2-0-feature-that-turns-facial-photos-into-personal-voices-over-potential-risks/)
- Jimeng/Doubao apps: users must record their own likeness **and voice** for real-person verification before they can create a digital avatar and appear in AI videos. The Jimeng web version, Doubao desktop/web and Xiaoyunque (小云雀) show "real-face reference not supported". — [Tencent News, 12 Feb 2026](https://news.qq.com/rain/a/20260212A05DJ200); [Zhihu](https://zhuanlan.zhihu.com/p/2004954350246715981)
- **15 Feb 2026:** Douyin Group VP Li Liang (李亮) said on Weibo that creating a digital avatar requires real-person authentication and that the platform temporarily does not support real-face reference or IP-character generation. — reported via [Zhihu](https://zhuanlan.zhihu.com/p/2004954350246715981) / [Tencent News](https://news.qq.com/rain/a/20260212A05DJ200) (search extract; I did not see the Weibo post itself)
- Official launch post wording: "If you wish to use real human portraits as subject references for video generation, identity verification or prior legal authorization is required." — quoted from the [Seedance 2.0 launch post](https://seed.bytedance.com/en/blog/official-launch-of-seedance-2-0) via [vicsee](https://vicsee.com/blog/seedance-2-0-face-workaround) / [GitHub ZeroLu how-to](https://github.com/ZeroLu/seedance2.0-how-to/blob/main/how-to-use-real-face-in-Seedance2.0.md)
- **Hollywood/copyright timeline (context for the tightening):**
  - Disney sent a cease-and-desist (mid-Feb 2026), calling the tool's treatment of its franchises "free public domain clip art" ([Deadline](https://deadline.com/2026/02/disney-bytedance-cease-and-desist-letter-seedance-ai-video-1236719549/)).
  - The MPA issued a statement and then a formal C&D, which the MPA called a "machine built for systemic infringement" ([Hollywood Reporter](https://www.hollywoodreporter.com/business/business-news/mpa-cease-and-desist-bytedance-seedance-2-0-1236510957/); [The Decoder](https://the-decoder.com/hollywoods-mpa-calls-bytedances-seedance-2-0-a-machine-built-for-systemic-infringement/)). Atlas Cloud's timeline dates the MPA C&D to 20 Feb ([Atlas Cloud](https://www.atlascloud.ai/blog/tips/is-hollywood-trying-to-shut-down-seedance-2.0)).
  - Netflix, Warner Bros., Paramount and Sony sent their own letters, and SAG-AFTRA objected over voices and likenesses.
  - On **16 Feb 2026** ByteDance pledged to "strengthen current safeguards… to prevent the unauthorized use of intellectual property and likeness" without specifics ([CNBC](https://www.cnbc.com/2026/02/16/bytedance-safegaurds-seedance-ai-copyright-disney-mpa-netflix-paramount-sony-universal.html)).
- **CapCut (intl):**
  - The phased rollout began **26 Mar 2026** for paid users in Brazil, Indonesia, Malaysia, Mexico, the Philippines, Thailand and Vietnam. TechCrunch also cites a report that the global rollout had been paused over Hollywood complaints ([TechCrunch, 26 Mar 2026](https://techcrunch.com/2026/03/26/bytedances-new-ai-video-generation-model-dreamina-seedance-2-0-comes-to-capcut/)).
  - CapCut's newsroom says the rollout restricts making videos "from images or videos that contain real faces" ([CapCut newsroom](https://www.capcut.com/newsroom/dreamina-seedance-2)). The search extract dates this post to 10 Apr 2026; TechCrunch's launch report is dated 26 Mar.
- **Dreamina (intl):** around 9–10 Feb 2026 Dreamina showed the note "does not support real human faces" under the model ([Alisa Qian on X](https://x.com/alisaqqt/status/2020877903102460321)). Uploads are rejected with "Face detected in your media. Try another one", and 2.0, 2.0 Fast and 2.0 Mini are all labeled "Real human faces are not supported" ([GitHub ZeroLu how-to](https://github.com/ZeroLu/seedance2.0-how-to/blob/main/how-to-use-real-face-in-Seedance2.0.md); [ruoqijin](https://ruoqijin.com/blog/seedance-access-and-face-policy)).
- **BytePlus ModelArk (API, intl), official:**
  - BytePlus "restrict[s] making videos from images or videos that contain real faces". Vetted clients "can complete real-person verification and likeness authorization through the ModelArk console" to use the likeness of people who gave permission. The 2.5 post repeats this. — [BytePlus blog, Seedance 2.0](https://www.byteplus.com/en/blog/dreamina-seedance2-0); [BytePlus blog, Seedance 2.5](https://www.byteplus.com/en/blog/dreamina-seedance2-5)
  - ModelArk docs: a **Private virtual portrait library** for Seedance 2.0/2.5, where assets must be legally owned and must **not resemble a real person**. It shares a quota with a separate **Real-human Portrait Library**, and full access needs "Advanced Creation Rights". References are addressed as "Image 1", "Video 1" and so on. — [BytePlus ModelArk docs: Private virtual portrait library](https://docs.byteplus.com/en/docs/ModelArk/2333565)
  - ModelArk docs, as quoted by a third party: "Seedance 2.5 and Seedance 2.0 series models do not support directly uploading reference images/videos that contain real human faces." — [SeedRouter](https://seedrouter.ai/blog/seedance-real-person-error)
  - The error returned is HTTP 400 `InputImageSensitiveContentDetected.PrivacyInformation` — [yingtu.ai](https://yingtu.ai/en/blog/seedance-2-0-human-face) (third-party)
- **Volcengine Ark (CN API):** the same privacy text applies, so direct real-face references are not accepted ([clipdance](https://clipdance.ai/blog/seedance-2-real-face-workaround), quoting Volcengine). A portrait-authorization invite can be sent from the Volcengine Ark experience center, and the depicted person scans a QR code to authenticate and authorize ([Zhihu, 14 methods](https://zhuanlan.zhihu.com/p/2037536880334463937); personal-experience article).
- **ComfyUI (official partner integration) shows the verified-asset flow concretely:**
  1. The "ByteDance Create Image/Video Asset" node returns a verification link.
  2. The user completes a liveness check on phone or browser (under 1 min).
  3. The node returns a **Group ID** (the person) and an **Asset ID** (that image).
  4. Later photos of the same person can be matched against the Group ID without re-verifying.
  Do not feed the real-face image directly; create the asset first. — [ComfyUI docs, Seedance 2.0 Real Human](https://docs.comfy.org/tutorials/partner-nodes/bytedance/seedance-2-0-real-human); [Comfy blog](https://blog.comfy.org/p/unlock-seedance20-real-human-video-generation); [Comfy-Org issue #822](https://github.com/Comfy-Org/workflow_templates/issues/822) (some users could not generate the verification link)
- Resellers: APIYI says realistic face references "are blocked by upstream content safety", and you must upload separately to get an `asset://` ID ([APIYI FAQ](https://docs.apiyi.com/en/faq/seedance2-asset-face-reference)). OrcaRouter documents a "trusted reference assets" library covering face, outfit, product or voice ([OrcaRouter docs](https://docs.orcarouter.ai/seedance-video/asset-library.md)). EvoLink claims real-face uploads work **without** identity verification ([EvoLink real-human guide](https://evolink.ai/blog/seedance-2-0-real-human-video-api-guide)), which contradicts upstream policy and is unverified.
- KIE markets "Seedance 2.0 API with **Realistic Human Support**" ([kie.ai/seedance-2-0](https://kie.ai/seedance-2-0)), but no extract explained what that means: an asset flow, pass-through, or simply that the model generates realistic humans.

### Inferences
- For the use case "a creator restyles **their own** face", the clean paths today are:
  - (a) **Jimeng app** in China: liveness-verified digital avatar of yourself. App only, not web.
  - (b) **BytePlus/Volcengine API** with real-person verification or likeness authorization, or a partner that wraps it (ComfyUI asset nodes).
  - (c) Avoid the face block entirely by using an AI-generated "styled self" image as the identity reference. This is less faithful, may still be caught when highly photoreal, and is not "your face" legally or visually.
- Dreamina international and CapCut consumers currently have **no self-verification route** documented. Treat them as unusable for real-face restyle.
- "Voice from photo" is gone. Any voice in the output should come from your own uploaded audio reference (or the post-dubbed original).

### Gaps
- No official October-2026 statement says whether any channel has relaxed the block. The latest dated sources are BytePlus's 2.5 materials (Jul–Aug 2026), which keep it.
- Not found: the exact eligibility criteria for "vetted clients" on BytePlus, Advanced Creation Rights pricing, and whether verified real-person assets can be used with **video** references (not just images) on the public API.
- Not found: KIE's actual behavior with real faces (pass-through block vs asset support). Test or ask KIE support before committing.
- One search extract claimed that the restriction does not apply to Seedance 1.5 Pro. I could not tie that claim to a specific citable source, so it is unverified.

## 4. Is there a newer Seedance than 2.0 by Oct 2026? And how do Seedance 1.0 / 1.5 Pro differ for this use case?

### Takeaway
Yes. **Seedance 2.5** launched officially on **31 Jul 2026**. It was previewed at Volcano Engine FORCE on 23 Jun 2026, is live on Dreamina and Jimeng, and its enterprise API on BytePlus ModelArk/Volcengine Ark followed in early August. It doubles clip length to **30 s per pass**, raises references to **30 images + 10 videos + 10 audio**, and adds timestamp-level editing. The real-face restrictions are unchanged. No official Seedance 2.1 or 3.0 video model exists ("Seed2.1" is a different, agent/LLM family). Seedance 1.5 Pro (Dec 2025) has native audio but no video-reference input, so it cannot do v2v restyle.

### Cited Findings
- Official blog dated **31 Jul 2026**: Seedance 2.5 builds on 2.0's unified audio-video joint architecture.
  - 30-second audio-video clips in one pass, with multi-round extension and better shot transitions.
  - Up to **30 images, 10 video clips, 10 audio clips** as references.
  - Timestamp-level targeted edits of audio and video, plus improved green-screen and other advanced features.
  — [ByteDance Seed, Introducing Seedance 2.5](https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5)
- Rollout:
  - Dreamina launched Seedance 2.5 worldwide on 31 Jul 2026 ([PR Newswire](https://www.prnewswire.com/news-releases/dreamina-launches-seedance-2-5--the-tool-of-ai-video-generation-that-reduces-clip-stitching-visual-drift-and-rework-302841204.html)).
  - At launch BytePlus said "Enterprise API access via BytePlus is coming soon" ([BytePlus on X](https://x.com/BytePlusGlobal/status/2083069262969844158)) and later "Dreamina Seedance 2.5 Enterprise API is now live on BytePlus" ([BytePlus on X](https://x.com/BytePlusGlobal/status/2085607384182145376); [BytePlus product page](https://www.byteplus.com/en/product/seedance)).
  - In China it rolled out to Jimeng, Doubao Pro and Xiaoyunque, with Volcengine Ark API to follow ([genape.ai](https://genape.ai/zh-CN/blog/what-is-seedance-2-5)).
  - FORCE preview date of 23 Jun: [Atlas Cloud](https://www.atlascloud.ai/blog/tips/seedance-2-5-release-date-4k-workflow-guide).
- 2.5 resolution is disputed. Some sources say BytePlus lists 480p/720p/1080p with no native 4K; others say the official API documents only 480p/720p and treat 4K as an upscale. — [ArgoLink, Oct 2026](https://argolink.io/en/blog/seedance-2-5-api-pricing); [cellcog](https://cellcog.ai/blog/seedance-2-5-pricing/); [aivideobootcamp](https://aivideobootcamp.com/blog/seedance-2-5-complete-guide-2026/). KIE advertises "30s 1080p" ([kie.ai/seedance-2-5](https://kie.ai/seedance-2-5)).
- 2.5 keeps the real-face restriction plus the verification route ([BytePlus 2.5 blog](https://www.byteplus.com/en/blog/dreamina-seedance2-5)). BytePlus also published a quality-enhancement post mentioning face and facial-feature stability ([BytePlus](https://www.byteplus.com/en/blog/dreamina-seedance-2-5-commercial-aigc-video-quality-enhancement)).
- Hands-on test: neither 2.0 nor 2.5 handled cross-shot consistency perfectly. The tester saw choppy transitions and changes in setting and time of day between shots. — [Kapwing, "Is Seedance 2.5 actually better than 2.0?"](https://www.kapwing.com/resources/is-seedance-2-5-actually-better-than-2-0-heres-what-i-found/)
- No official Seedance 2.1 video model was found as of 7 Aug 2026; "Seed2.1" is an unrelated agent/productivity family ([EvoLink 2.1 status](https://evolink.ai/blog/seedance-2-1-release-watch-evolink-prep)). No official Seedance 3.0 announcement had appeared as of Jul 2026 ([clipdance 3.0 page](https://clipdance.ai/seedance-3-0)).
- **Seedance 1.5 Pro (Dec 2025):**
  - Native joint audio-video with millisecond-level lip-sync. Lip-sync languages: ZH, EN, JA, KO, ES (some sources add Indonesian).
  - Duration 4–12 s.
  - Resolution: 480p/720p per Artlist/Sousaku; aggregators claim 1080p.
  - Image-to-video from a start frame. There is **no reference-video input**.
  — [Artlist blog](https://artlist.io/blog/seedance-1-5-ai-announcement/); [MindStudio](https://www.mindstudio.ai/blog/what-is-seedance-1-5-pro-bytedance-video); [Sousaku](https://sousaku.ai/en/models/seedance-pro-1.5); [KIE 1.5 Pro docs](https://docs.kie.ai/market/bytedance/seedance-1-5-pro)
- Seedance 1.0 was a visual-only model without joint audio. — [stackshare comparison](https://stackshare.io/stackups/lip-sync-ai-vs-seedance-2-0-mmei3lsl)

### Inferences
- For talking-head restyle, **2.5 is the better fit than 2.0** if budget allows. The 30 s cap halves the number of seams in a 3–5 min video, and its more references and timestamp edits help fix single bad moments without re-rolling the whole clip.
- 1.0 and 1.5 Pro are irrelevant for v2v. 1.5 Pro could only animate a restyled still with generated speech, which would be a weaker version of the OmniHuman approach (§6).

### Gaps
- I could not read the full 2.5 blog. Its official resolution list, max reference-video total (KIE suggests 30 s combined) and per-file limits are from extracts and resellers.
- Exact date of BytePlus/Volcengine 2.5 API general availability: sources say "early August", but I found no precise official date.

## 5. Programmatic access and prices: BytePlus ModelArk, Volcengine, KIE.ai, fal.ai, Replicate, WaveSpeed

### Takeaway
Official access is **BytePlus ModelArk** (international) or **Volcengine Ark / 火山方舟** (China). Both bill by tokens, which works out to about **$0.15/s at 720p and $0.37/s at 1080p** for Seedance 2.0 without video input. With a reference video the per-token rate is lower, but input video seconds are billed too. **KIE.ai** offers the same models behind an async `createTask` → callback or `recordInfo` poll API, and appears cheapest for 2.0, with credit pricing at 200 credits = $1. fal and Replicate charge roughly 2× ($0.24–0.30/s at 720p). For 2.5, BytePlus lists about $0.23/s at 720p; KIE's beta 2.5 pricing is $0.19/s with video input and $0.315/s without at 720p.

### Cited Findings
- **BytePlus ModelArk, Seedance 2.0 token pricing** (third-party transcriptions of the BytePlus price page, Sep 2026):
  - Without video input: 480p and 720p **$7.00 per 1M tokens**, 1080p **$7.70**.
  - With video input: **$4.30** (480p/720p) and **$4.70** (1080p).
  - 2.0 Fast: $5.60 without video and $3.30 with video, no 1080p.
  - Token formula: (input video s + output video s) × width × height × fps ÷ 1024.
  - Per-second equivalents: about $0.15/s at 720p and $0.37/s at 1080p.
  — [framesurfer](https://framesurfer.com/blogs/seedance-2-0-pricing); [LumiYing](https://lumiying.com/resource/seedance-2-pricing); [Quill Router PR #1546](https://github.com/Lore-Hex/quill-router/pull/1546)
- **BytePlus, Seedance 2.5:**
  - About **$10.70/1M tokens** without video and **$6.40** with video at 480p/720p ([ClipDance](https://clipdance.ai/blog/seedance-2-5-pricing)).
  - Per second without video input: $0.1028 (480p), **$0.2311 (720p)**, $0.5686 (1080p). A 5 s 720p clip costs $1.156 ([GlobalGPT](https://www.glbgpt.com/hub/seedance-2-5-pricing/)).
- **KIE.ai API shape:**
  - `POST https://api.kie.ai/api/v1/jobs/createTask` with a Bearer key and body `{"model": "bytedance/seedance-2" | "bytedance/seedance-2-fast" | …, "callBackUrl": "...", "input": {...}}`.
  - Status: `GET https://api.kie.ai/api/v1/jobs/recordInfo?taskId=…`. Poll until state is `success` or `fail`. Some video tasks exceed 10 min.
  - The optional `callBackUrl` receives a POST with the same body as `recordInfo`.
  — [KIE docs: Seedance 2.0](https://docs.kie.ai/market/bytedance/seedance-2); [KIE docs: Get Task Details](https://docs.kie.ai/market/common/get-task-detail); [vas.mintlify KIE skill](https://vas.mintlify.app/skills/create-video-seedance-2-0); [popularaitools](https://popularaitools.ai/blog/seedance-2-api-kie-ai-2026)
- **KIE `input` fields:** `prompt`, `reference_image_urls[]`, `reference_video_urls[]`, `reference_audio_urls[]`, `first_frame_url`, `last_frame_url`, `duration`, `aspect_ratio`, `resolution`, `generate_audio` (default true). Media are passed as public HTTPS URLs; KIE also has a File Upload API.
  - 2.0 limits: images ≤30 MB (max 9), videos ≤50 MB (max 3; MP4/MOV/MKV).
  - 2.5 limits: up to 30 images ≤30 MB and 10 videos ≤200 MB.
  — [KIE docs: Seedance 2.0](https://docs.kie.ai/market/bytedance/seedance-2); [KIE docs: Seedance 2.5](https://docs.kie.ai/market/bytedance/seedance-2-5); [kie.ai/seedance-2-5](https://kie.ai/seedance-2-5)
- **KIE prices, Seedance 2.0** (page about 225 days old at search time):
  - 480p: **6.8 credits/s with video input**, 11.7 without.
  - 720p: **15 credits/s with video input**, 24.8 without.
  - No 1080p price was shown in the extract.
  — [kie.ai/seedance-2-0](https://kie.ai/seedance-2-0)
  - KIE credit rate: **1 USD = 200 credits** (stated on the KIE OmniHuman page) — [kie.ai/omnihuman-1-5](https://kie.ai/omnihuman-1-5)
  - Atlas Cloud's comparison lists KIE 2.0 720p at about $0.125/s, labeled "with video input" — [Atlas Cloud](https://www.atlascloud.ai/blog/guides/seedance-2.0-api-pricing-the-cheapest-provider-compared). Atlas Cloud is a competitor, and the label conflicts with KIE's own table (24.8 cr ≈ $0.124 is the *without*-video rate).
- **KIE prices, Seedance 2.5** (marked "beta, may be adjusted"):
  - 480p: $0.085/s with video input, $0.140/s without.
  - 720p: **$0.190/s** with video input, **$0.315/s** without.
  - 1080p: $0.475/s with video input, $0.790/s without.
  - Reference-video seconds are billed in addition to output seconds. Image and audio references add no billable seconds.
  — [kie.ai/seedance-2-5](https://kie.ai/seedance-2-5); confirmed by [ArgoLink, Oct 2026](https://argolink.io/en/blog/seedance-2-5-api-pricing)
- **KIE 2.0 Mini billing:** with reference video, a lower per-second price is charged on (total reference duration + output duration). Total reference video ≤15 s. — [KIE docs: Seedance 2.0 Mini](https://docs.kie.ai/market/bytedance/seedance-2-mini)
- **fal.ai:** Seedance 2.0 at 720p costs **$0.30/s (Standard)** and $0.24/s (Fast), with no minimums ([fal.ai/seedance-2.0](https://fal.ai/seedance-2.0); live on fal since April 2026). Third parties list fal 1080p at about $0.682/s ([poyo.ai comparison](https://poyo.ai/comparison/seedance-2-fal-vs-replicate-vs-poyo)).
- **Replicate:** figures are inconsistent. One source says about $0.18/s at 720p and $0.08/s at 480p; another says Replicate matches fal (about $0.30/s at 720p). — [wireflow](https://www.wireflow.ai/blog/seedance-pricing-compared-2026); [poyo.ai](https://poyo.ai/comparison/seedance-2-fal-vs-replicate-vs-poyo); model page: [replicate.com/bytedance/seedance-2.0](https://replicate.com/bytedance/seedance-2.0)
- **WaveSpeed:** about $0.24/s at 720p ($1.20 per 5 s), $0.12/s at 480p and $0.60/s at 1080p. It has a separate `video-edit` endpoint. — [apiframe comparison](https://apiframe.ai/models/seedance-2.0/pricing); [WaveSpeed video-edit](https://wavespeed.ai/models/bytedance/seedance-2.0/video-edit)
- Other aggregators: Atlas Cloud about $0.112/s for 2.0 and $0.090/s for Fast ([Atlas Cloud](https://www.atlascloud.ai/blog/guides/seedance-2.0-api-pricing-the-cheapest-provider-compared)); EvoLink $0.121/s at 720p ([EvoLink](https://evolink.ai/seedance-2-0)).

### Inferences
- These are my own calculations from the cited rates:
  - **Official BytePlus, 2.0 at 720p, 15 s output with a 15 s reference video:** 30 s × (1280×720×24/1024 = 21,600 tokens/s) × $4.30/M ≈ **$2.79 per clip**. The same clip without video input is ≈ $2.27.
  - **KIE 2.0 at 720p with video input:** 15 cr/s ≈ $0.075/s. If KIE also bills reference + output seconds (documented for Mini and 2.5, not confirmed for 2.0), 30 s ≈ **$2.25 per clip**.
  - **KIE 2.5 at 720p, 30 s output with a 30 s reference:** 60 s × $0.19 ≈ **$11.40 per clip**.
  - **Whole video:** a 4-minute talking head restyled on KIE 2.5 at 720p is ≈ 8 clips ≈ **$90 per pass**. On KIE 2.0 at 720p it is ≈ 16 clips ≈ **$36 per pass**. Re-rolls for failed clips come on top.
- Cheapest-to-most-expensive for 2.0 at 720p: KIE ≈ Atlas < BytePlus official < WaveSpeed < fal ≈ Replicate (upper estimate). KIE's 2.5 beta price is above BytePlus list for the no-video case.
- With video references, "with video input" pricing applies. It is lower per token but bills input seconds, so the effective cost per output second roughly doubles versus the headline rate when the reference length equals the output length.

### Gaps
- Not confirmed from the docs: KIE 2.0 1080p price, KIE's exact `duration`, `aspect_ratio` and `resolution` enums, the KIE 2.5 model ID string, and whether the KIE 2.0 "with video input" rate is billed on reference + output seconds.
- No official BytePlus or Volcengine price page could be read directly. The figures come from third-party transcriptions dated around Sep 2026.
- Volcengine (CNY) pricing for the China API was not found.

## 6. OmniHuman (1.5) — photo + voice → talking video as an alternative to v2v restyle

### Takeaway
OmniHuman 1.5 is ByteDance's audio-driven avatar model. You give it a single image plus an audio track (plus an optional text prompt for emotion, gesture and camera), and it generates a lip-synced talking or acting video. It handles **up to 60 s of audio at 720p or 30 s at 1080p** per call and costs about **$0.12–0.16/s** across providers. The audio drives the output, so **your original voice is preserved and lip-sync is the model's core strength**. Your actual filmed gestures and performance are **not** preserved; the body language is generated. No OmniHuman 2.0 is confirmed as of Oct 2026.

### Cited Findings
- Audio length is ≤60 s at 720p and ≤30 s at 1080p, with 1080p the default resolution. Prompts work best as "mini-screenplays" covering camera direction, emotional arc, speaking state and sequential actions, because the model reasons semantically and does more than sync to audio. — [fal OmniHuman 1.5 user guide](https://fal.ai/learn/devs/omnihuman-15-user-guide); [fal prompt guide](https://fal.ai/learn/devs/omnihuman-1-5-prompt-guide); [fal 1.5 vs 1.0 comparison](https://fal.ai/learn/biz/omnihuman-15-vs-omnihuman-comparison)
- OmniHuman 1.5 adds MLLM-based semantic planning for context-aware emotion and gestures, multi-person scenes and longer, more continuous video. — [rekreate.ai](https://rekreate.ai/models/omnihuman). Multi-person images use a mask index to pick the speaker, according to one source ([evolink review](https://evolink.ai/blog/omnihuman-1-5-review-bytedance-ai-avatar-generator-ultimate-guide)).
- Prices:
  - BytePlus official page: **$0.12/s**, which conflicts with Pixazo's attribution of $0.16/s to BytePlus ([BytePlus OmniHuman](https://www.byteplus.com/en/product/OmniHuman); [Pixazo](https://www.pixazo.ai/models/omnihuman)).
  - fal: **$0.16/s** of output ([fal guide](https://fal.ai/learn/devs/omnihuman-15-user-guide)).
  - PiAPI: $0.13/s, billed on input audio length ([PiAPI guide](https://piapi.ai/tr/blogs/omnihuman-1-5-api-guide)).
  - EvoLink: about $0.176/s (12 credits/s), billed on audio duration, with audio capped at 35 s ([EvoLink](https://evolink.ai/omnihuman-1.5)).
  - ModelsLab $0.14/s and AIMLAPI $0.156/s ([ModelsLab](https://modelslab.com/models/byteplus/omnihuman-1.5); [AIMLAPI](https://aimlapi.com/models/omnihuman-v1-5)).
- KIE has an OmniHuman 1.5 product page ("ByteDance AI Avatar & Digital Human API"). Its pricing varies by sub-model at 1 USD = 200 credits, and no per-second rate appeared in the extracts. — [kie.ai/omnihuman-1-5](https://kie.ai/omnihuman-1-5)
- OmniHuman 1.0 dates from a Feb 2025 research paper. The only "OmniHuman 2" mention found is a bare EachLabs listing with no specs. — [fal OmniHuman](https://fal.ai/models/fal-ai/bytedance/omnihuman); [EachLabs](https://www.eachlabs.ai/bytedance)

### Inferences
- These comparisons are mine, built from the cited specs:
  - **OmniHuman path:** take one still of yourself, restyle it with an image model (outfit, era, location, art style), then feed it with your **original** audio in chunks of 60 s or less (720p) or 30 s or less (1080p).
    - Strengths: your real voice stays untouched, there are about 4–8 calls for a 4-minute video, and lip-sync is the model's core strength.
    - Weaknesses: your filmed gestures, head turns and expressions are replaced with generated ones; the background is mostly static per call; and identity comes from one still.
  - **Seedance v2v path:**
    - Strengths: it keeps your blocking and timing, and costume or background can change dynamically.
    - Weaknesses: ≤15 s per clip on 2.0 (≤30 s on 2.5), audio is regenerated, lip-sync is approximate, and the face block applies.
- Price per output second is similar: OmniHuman about $0.12–0.16/s vs Seedance 2.0 about $0.08–0.30/s. OmniHuman needs far fewer seams per minute, though.
- A hybrid is plausible: Seedance for the B-roll and "transformation" moments, OmniHuman or a lip-sync tool for long monologue stretches.

### Gaps
- Not found: whether OmniHuman 1.5 on BytePlus, Dreamina or KIE applies the **same real-face block** as Seedance. It is unverified either way; check before relying on a real photo of yourself.
- KIE's exact OmniHuman per-second price and endpoint names were not retrieved.
- Not found: an official ByteDance statement on an OmniHuman successor.

## 7. Typical failure modes for talking-head use (identity drift, lip-sync drift, flicker between clips, hands/teeth, inconsistent background in a 3–5 min video)

### Takeaway
The documented failure modes, mostly from guides and a few creator tests, are:
- identity drift late in 10–15 s clips;
- "twins" (duplicate characters) when multi-view reference sheets are used;
- lip-sync drift or failure on longer references (about 13 s or more) and late in 15 s clips;
- the model altering spoken words;
- output audio not identical to the reference;
- discontinuities between separately generated clips (setting and lighting shifts, choppy transitions).
I found no hard data on teeth or hands artifacts or on multi-minute background flicker. A 3–5 min piece necessarily means 6–20 stitched generations with seams.

### Cited Findings
- Identity drift: guides say to "expect some identity drift near the end" of 10 s photoreal face clips. Multi-angle character sheets are read as several people, which causes the "twins" bug. A tight face headshot plus one full-body shot works better than filling every slot. — [sagnikbhattacharya](https://sagnikbhattacharya.com/blog/seedance-2-lip-sync-talking-head); [Morphic guide](https://morphic.com/resources/how-to/seedance-2-guide) (search-extract attribution across these two guides is not certain)
- Lip-sync drift: sync can drift late in 15-second clips and in foley-heavy shots ([Cutout.pro audio guide](https://www.cutout.pro/learn/blog-seedance-2-0-audio-guide/); [UGC Copilot](https://ugccopilot.ai/blog/seedance-2-native-audio-generation-guide/)). Tight word-level sync "still needs review" ([sagnikbhattacharya](https://sagnikbhattacharya.com/blog/seedance-2-lip-sync-talking-head)). High-res, well-lit, front-facing references give tighter sync ([seedance-2.app](https://seedance-2.app/blog/seedance-2-0-lip-sync)).
- Creator, May 2026: reference video over about 13 s broke lip-sync, the model sometimes changed lyrics, and it sometimes did not lip-sync to the reference image. — [Abdullah Yahya](https://abdullahyahya.com/2026/05/make-realistic-lip-sync-music-videos-with-seedance-2-0/)
- Off-sync fixes are covered in [CrePal, "What works, what breaks"](https://crepal.ai/blog/aivideo/blog-seedance-2-0-lip-sync-voiceover-fix/).
- Cross-clip consistency: neither 2.0 nor 2.5 handled it perfectly in a hands-on test, with choppy transitions and setting or time-of-day changes between shots ([Kapwing](https://www.kapwing.com/resources/is-seedance-2-5-actually-better-than-2-0-heres-what-i-found/)). Expect iteration on wardrobe changes and longer shot chains ([BudgetPixel](https://budgetpixel.com/models/seedance-2.0-mini)). Stitched short clips "dissolve" character and lighting at the seam, according to Atlas Cloud's 2.5 marketing ([Atlas Cloud](https://www.atlascloud.ai/blog/guides/seedance-2-5-30-second-ai-video-ads)).
- Length: direct generation is 4–15 s, and creators "generate multiple short segments and then stitch them together" ([Magic Hour best-settings](https://magichour.ai/blog/seedance-20-best-settings); [Creatify](https://creatify.ai/es/blog/seedance-is-now-in-creatify-asset-generator)). ByteDance's own Dreamina 2.5 launch pitches 2.5 as reducing "clip stitching, visual drift and rework" ([PR Newswire](https://www.prnewswire.com/news-releases/dreamina-launches-seedance-2-5--the-tool-of-ai-video-generation-that-reduces-clip-stitching-visual-drift-and-rework-302841204.html)), which implicitly acknowledges these as 2.0 pain points.
- Face filter as an operational failure: highly realistic **AI-generated** faces can also trip the real-person check, so the "AI portrait" workaround is not guaranteed. — [clipdance](https://clipdance.ai/blog/seedance-2-real-face-workaround)
- Over-referencing: filling every reference slot causes style conflicts ([Magic Hour](https://magichour.ai/blog/seedance-20-reference-guide)).

### Inferences
- For a 3–5 min restyled talking head, the dominant risks are:
  - (1) **seams**: costume details, background props and lighting shift between clips, because each clip is an independent generation;
  - (2) **progressive identity drift** within each clip's last seconds;
  - (3) **mouth mismatch**, where regenerated lips don't match re-laid original audio.
- Mitigations implied by the sources:
  - keep clips at 13 s or less on 2.0;
  - reuse the *same* identity and outfit reference images and the same background image across all clips;
  - avoid hard cuts mid-sentence;
  - use 2.5's 30 s clips or timestamp edits to cut the seam count;
  - budget re-rolls of about 1.5–2× (my estimate, not sourced).

### Gaps
- **No sourced data on teeth or hand artifacts** specific to Seedance talking heads. Searches returned nothing concrete.
- **No Reddit (r/aivideo, r/StableDiffusion) or X threads** with systematic multi-minute talking-head restyle results were found in searches. The evidence is mostly vendor or guide content and is likely biased positive.
- No quantitative lip-sync metrics (e.g., LSE-C/D) published for Seedance 2.0/2.5 vs OmniHuman were found.
