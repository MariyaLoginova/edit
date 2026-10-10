# AI-avatar "talking head" restyle: practitioner tutorials and real creator workflows (2025 – Oct 2026)

> **Method and reliability note (read first).** Research date: 2026-10-10. In this session the egress proxy blocked direct page fetches to every host I tried (youtube.com, reddit.com, x.com, vc.ru, habr.com, help.runwayml.com, docs.comfy.org and others). The search API also refuses reddit.com. Everything below therefore comes from **search-engine result titles, URLs and summaries/snippets**, not from reading full pages or watching videos. Every URL listed was returned by the search engine, so it exists, but I could not open it to check its full contents. **Dates:** X/Twitter post dates are decoded from the status/article ID (Twitter "snowflake" timestamp; my computation). Most YouTube upload dates and channel names were **not** in the results and are marked "date n/a". Many hits are SEO or vendor blogs (seedance.tv, cutout.pro, magichour, wavespeed, vicsee and the like). I flag them as secondary where relevant.

## 1. Which tutorials show the workflow step by step (Seedance 2.0; Kling/Runway Aleph/Luma/Higgsfield; ComfyUI Wan Animate/VACE; matting plus AI background)?

### Takeaway
There are plenty of step-by-step tutorials for each tool. However, I found **no single verified tutorial that walks through the exact "film yourself talking → restyle outfit/era/location → keep your own voice and lip-sync" pipeline** end to end. Practitioners assemble it from four kinds of tutorial:
- Seedance 2.0 "Omni reference"/video-edit tutorials, the strongest model for character swap and lip-sync. Its big catch is the real-face upload ban.
- Runway Aleph 2.0, Kling O1/3.0 Omni Edit, Luma Modify and Higgsfield Genjutsu "edit only X" tutorials.
- Wan 2.2 Animate "Mix/replace" tutorials in ComfyUI.
- Matting tutorials (CapCut Auto Removal, Robust Video Matting, SAM2) that composite the speaker over a separately generated background.

### Cited Findings

**(a) Seedance 2.0: video reference, restyle, character swap and lip-sync**
- Seedance 2.0 was released by ByteDance in **February 2026** — [Choosely: Chloe vs History AI stack](https://choosely.ai/ai-radar/chloe-vs-history-ai-stack).
- YouTube, "Complete Seedance 2.0 Video Reference Tutorial" (date n/a). Covers using video references to control motion, camera moves and visual style — [YouTube](https://www.youtube.com/watch?v=ikPGQGoUjQ0&vl=en).
- YouTube, "Seedance 2.0 Video Reference Tutorial (How to Use Video-to-Video)" (date n/a) — [YouTube](https://www.youtube.com/watch?v=wybn1PhFVHY).
- YouTube, "How to use your own face and voice in seedance 2.0 [Step-By-Step] Guide" (date n/a; the search summary says it promotes a third-party platform) — [YouTube](https://www.youtube.com/watch?v=UgCcDWVhRN8).
- YouTube, "Seedance 2.0 Video References — Fixing the Face & Audio Problem" (date n/a; per the search summary it covers face consistency, audio restrictions and stylized results) — [YouTube](https://www.youtube.com/watch?v=4V5aGqlT8mw).
- YouTube, "How to Edit Real Human Videos in Seedance 2.0 Without Failing Moderation" (date n/a). The title confirms that moderation of real-human footage is a practical obstacle — [YouTube](https://www.youtube.com/watch?v=r5lrBRJLXXY).
- YouTube Short "Seedance 2.0" (date n/a). Per the search summary, 2.0 is good at changing environments, outfits and overall visual style of existing footage while keeping the original performance and movement — [YouTube Shorts](https://www.youtube.com/shorts/VAFXn85HWAw).
- YouTube, "Seedance 2.0 outperforms Kling, Runway Aleph, and Luma in video modification. Cinema 4D + AI." (date n/a) — [YouTube](https://www.youtube.com/watch?v=GqyohMi8Dvg).
- YouTube, "How to FIX Vehicle, Character & Environment Consistency: Seedance 2.0 (+ FREE PROMPTS)" (date n/a) — [YouTube](https://www.youtube.com/watch?v=01V0M3vI94Q).
- YouTube, "How to Keep the Same Character Voice Across Every Generation using Seedance 2.0" (date n/a) — [YouTube](https://www.youtube.com/watch?v=lOa3oiUal-M). See also "Seedance 2.0 Tutorial: Perfect Character + Voice Consistency Workflow in Runway AI" — [YouTube](https://www.youtube.com/watch?v=SWhYbZxRZCA).
- X, Travis Davids (@MrDavids1), **2026-04-14**: "Seedance 2.0 has the most accurate character swap available". The method is to upload the source video as an **OMNI Reference** plus an image of the replacement character. Scene continuity, camera motion and character movement were all maintained — [X](https://x.com/MrDavids1/status/2043891653346283606).
- X, Travis Davids, **2026-04-16**, crediting @simeonnz. If you upload audio directly, Seedance 2.0 "changes the lyrics and even the song itself". Saving a **blank video containing the audio** and uploading that video fixes it — [X](https://x.com/MrDavids1/status/2044600846416068714).
- X, Curious Refuge, **2026-05-05**. They tested Seedance 2.0 multi-speaker lip-sync across live action and animation and found it "working really well". Inputs were a reference image, a blacked-out video with audio (or an audio file), and a prompt that combines camera motion with the dialogue — [X](https://x.com/CuriousRefuge/status/2051768714224414749).
- Curious Refuge blog, "The Latest AI Lip Sync Techniques" (date n/a). In their live-action lip-sync examples Seedance 2.0 "performed the best" and LTX 2 Fast "fell behind a bit". They recommend Seedance 2.0 for live action "if it works", and HeyGen for avatar-style live-action lip-sync — [Curious Refuge](https://curiousrefuge.com/blog/ai-lip-sync-workflows).
- X article, GumVue, "How to Get Consistent Voices for AI Actors in Seedance 2.0", **2026-06-16** — [X](https://x.com/GumVue/article/2066700181161001277).
- OpenArt, "The Seedance 2.0 Handbook" (date n/a):
  - Upload images, videos and audio as references, then tag them in the prompt with **@**.
  - If a reference video has its own audio and you also tag a separate audio file, the model "tends to favor the video's existing audio". The workaround is to upload the video without audio.
  - [OpenArt](https://openart.ai/blog/seedance-2-0-handbook/)
- Medium, "How to Use Reference Video in Seedance 2.0 to Copy Motion & Camera Moves" (date n/a) — [Medium](https://medium.com/@social_18794/how-to-use-reference-video-in-seedance-2-0-to-copy-motion-camera-moves-6ee78dd117e7).
- Seegen.ai "Seedance 2.0 Audio Reference Guide" (secondary, date n/a):
  - Convert each audio segment into a **black-screen MP4** and use it as the video reference, for stricter lip-sync timing.
  - Includes an example that changes outfit and background while keeping lines locked to the audio.
  - [Seegen](https://seegen.ai/seedance-2-0-audio-guide)
- WaveSpeed guide (secondary) lists **Video Edit / Video Edit Turbo** endpoints for Seedance 2.0, including character replacement that keeps the original action — [WaveSpeed](https://wavespeed.ai/blog/posts/seedance-2-0-complete-guide-multimodal-video-creation/).
- Picsart offers "Seedance 2.0 Edit" in its AI Playground: upload a clip, write the edit, no regeneration from scratch. The search summary describes it as useful for background, outfit or lighting changes — [Picsart post (raw WP-JSON URL returned by search)](https://picsart.com/blog/wp-json/wp/v2/posts/254652) *(details came from a search summary; the human-readable Picsart page URL was not isolated)*.
- Russian-language Seedance guides:
  - vc.ru (Prompt Studio), «Seedance 2.0 - продвинутый гайд: своё лицо в кадре, русская речь и редактирование готовых видео через @video1» (date n/a). It covers three scenarios: holding a real person's face across shots, making a character speak Russian (write the Russian line in **transliteration**), and restyling your own video via **@video1**. Key trick: explicitly reference **@image1** in the prompt, otherwise the photo is treated as "inspiration" and may be ignored — [vc.ru](https://vc.ru/ai/2919130-seedance-2-0-prodvinutyi-gayd).
  - vc.ru, «Полное руководство по Seedance 2.0» (date n/a). Includes a remix prompt that replaces the clothes of the person in @Video1 with the clothes in @Image1 — [vc.ru](https://vc.ru/ai/2748739-seedance-2-0-polnoe-rukovodstvo).
  - vc.ru (Prompt Studio), «Seedance 2.0: полный гайд по видео-нейросети ByteDance - модели, режимы, цены и 6 готовых промптов» (date n/a) — [vc.ru](https://vc.ru/promtstudio/2919129-seedance-2-0-gayid-po-video-neyroseti-bytedance).
  - vc.ru, «Seedance 2.0 - лица, русская речь и промты. Как создавать видео нейросетью без ограничений.» (date n/a) — [vc.ru](https://vc.ru/promtstudio/2817087-seedance-2-0-kak-sozdat-video-neirosetyu).
  - Habr (tsnis), «Оживить фото в Seedance 2.0: как сделать видео со своим лицом, несмотря на цензуру» (date n/a) — [Habr](https://habr.com/ru/companies/tsnis/articles/1031512/).
  - Habr (study_ai), «Seedance 2.0 и версия Pro: Как пользоваться нейросетью для генерации видео в России» (date n/a) — [Habr](https://habr.com/ru/companies/study_ai/articles/1044872/).
  - dsgners.ru, «Seedance 2.0: полный гайд по работе с нейросетью. 15 промптов» (date n/a). @Image1 can be designated as face, clothing and silhouette, and the face should be pinned with a separate instruction when changing clothes — [dsgners](https://dsgners.ru/yelpin/42655-seedance-2-0-polnyiy-gayd-po-rabote-s-neyrosetyu-15-promptov).
  - DTF, «Seedance 2.0: как пользоваться нейросетью для генерации видео по тексту, фото и референсам в 2026 году» — [DTF](https://dtf.ru/howto/5078770-seedance-2-0-kak-ispolzovat-neyroset-dlya-generatsii-video).
  - NeuroLena (Substack), «Seedance 2.0: полное руководство по ИИ-видео» — [Substack](https://neurolena.substack.com/p/seedance-20).
  - Sostav, «🔥 Как вставить себя в видео с помощью ИИ — замена персонажа через нейросеть» (2026). Workflow: a short video with a person in frame plus a photo of the person to insert. For a first test, use a short clip where the face is clearly visible — [Sostav](https://www.sostav.ru/blogs/287935/98689).

**(b) Kling O1 / 3.0 Omni Edit, Runway Aleph, Luma Modify, Higgsfield**
- Runway, "Aleph 2.0 Prompting Guide" (official help center, date n/a):
  - Wardrobe example: "Change the outfit and bag to soft yellow."
  - For backgrounds, describe the new setting; Aleph 2.0 substitutes it while preserving subject and foreground.
  - [Runway Help](https://help.runwayml.com/hc/en-us/articles/52150503729171-Aleph-2-0-Prompting-Guide)
- Runway, "Introducing Aleph 2.0" (official video, date n/a). You edit a **single frame**, preview the change, and Aleph 2.0 carries it across the clip — [YouTube](https://www.youtube.com/watch?v=8vAqhBxCxc0).
- YouTube Aleph tutorials (all date n/a):
  - "How To Use RunwayML Aleph 2.0 In Edit Studio (Step-By-Step)" — [YouTube](https://www.youtube.com/watch?v=ulQRsF3Moec)
  - "How to Use Aleph 2.0 in Edit Studio" — [YouTube](https://www.youtube.com/watch?v=-lVVZDuEIVs)
  - "How to Transform Videos with Runway Aleph" (has an "Using image references" chapter) — [YouTube](https://www.youtube.com/watch?v=7Ga0H4Tr3Fg)
  - "Runway Aleph: How I Turned One Video Into Multiple Worlds" — [YouTube](https://www.youtube.com/watch?v=IsQELAbxVVU)
  - "NEW Runway ALEPH Lets You Change Anything in a Video - 20 Examples" — [YouTube](https://www.youtube.com/watch?v=yYQmPNuAUIc)
  - Russian: «Runway Aleph 2: Нейросеть, которая меняет всё в видео!» (objects, clothing, background) — [YouTube](https://www.youtube.com/watch?v=IOLH3KSzPDc)
- Curious Refuge, "9 Practical Ways to Use Runway Aleph" (with video). A walking woman was given a black leather coat; it integrated with scene lighting and the texture held up after 4K upscaling. This is a general clip, not a talking head — [Curious Refuge](https://curiousrefuge.com/blog/9-ways-to-use-runway-aleph).
- Framia, "How to use Runway Aleph 2" (secondary). Make one change per generation, chain edits in sequence, and use the still-image preview to save credits — [Framia](https://framia.converge.ai/page/en-US/blog/how-to-use-runway-aleph-2).
- Kling O1:
  - fal "Kling O1 prompt guide": in video-to-video edit mode, state first what must remain unchanged (camera movement, subject blocking, background elements), then the single change — [fal](https://fal.ai/learn/devs/kling-o1-prompt-guide)
  - fal launch post — [fal blog](https://blog.fal.ai/introducing-kling-o1-video-available-exclusively-as-an-api-on-fal)
  - Higgsfield "Kling O1 prompt bank" — [Higgsfield](https://higgsfield.ai/blog/kling-O1-prompt-bank)
- Kling 3.0 Omni (the "Kling O3" family) launched **February 2026**. Its video-to-video edit transforms existing footage via text prompts (background swaps, inserting characters) without manual masking — [Segmind](https://www.segmind.com/models/kling-o3-video2video-edit).
  - Media.io's Kling editor takes up to 4 reference images and uses the syntax "Change [subject] in [@Video] to [@Image]". Inputs are mp4/mov, ≤200 MB, **3–10 s**, 720p–2160p, 24–60 fps — [Media.io](https://www.media.io/ai/video-edit/kling-ai-video-editor).
  - Unifically API offers **Reference** and **Transform** modes and a **keep_audio** option; output length follows input length — [Unifically](https://unifically.com/models/kling-3.0-omni-edit).
  - Picsart describes Omni Edit as masking specific areas to swap clothing or backgrounds — [Picsart](https://picsart.com/ai-models/kling-3-0-omni/).
- Luma Modify Video:
  - Official announcement: "keep the performance, change the world" — [Luma](https://lumalabs.ai/news/introducing-modify-video)
  - Changelog example: change an outfit "from casual clothes to a medieval costume". Edits use pose, facial expression and scene-structure signals — [Luma changelog](https://lumalabs.ai/changelog/introducing-modify-video)
  - **Ray3 Modify** (announced **2025-12-18**) adds Start/End Frame and a **Character Reference** that locks likeness, costume and identity across a clip — [YourStory](https://yourstory.com/ai-story/luma-ai-ray3-modify)
  - Scenario help, "Luma Modify Video – The Essentials" — [Scenario](https://help.scenario.com/articles/4556939523-luma-modify-video-the-essentials)
- Higgsfield **Genjutsu**: an object-swap mode where you point at an outfit, location, character or object and change only that; supports **3–30 s** source videos. The underlying model was not stated — [Higgsfield](https://higgsfield.ai/genjutsu). Higgsfield's general Seedance 2.0 tutorial — [Higgsfield blog](https://higgsfield.ai/blog/generating-with-seedance-2-0).

**(c) ComfyUI Wan 2.2 Animate / Wan Animate 2 (replace yourself)**
- Official Comfy docs, "Wan2.2 Animate". Replaces characters while keeping the performer's expressions and movements and matching scene lighting and colour — [docs.comfy.org](https://docs.comfy.org/tutorials/video/wan/wan2-2-animate.md).
- Comfy workflow page: pose via **DWPreprocessor**, subject isolated via **SAM2** (mark the person with green points), width and height must be multiples of 16 — [comfy.org](https://comfy.org/workflows/video_wan2_2_14B_animate-c2c4b45b7df5/).
- "Wan Animate 2 is now available in ComfyUI" (native support) — [Comfy blog](https://blog.comfy.org/p/wan-animate-2-is-now-available-in).
- Wan Animate 2 tutorial (secondary). **Mix** mode replaces the person in the driving video and keeps the original scene, background and **sound**. **Move** animates a still character image — [seedance.tv](https://www.seedance.tv/blog/wan-animate-2-tutorial).
- ComfyUI-Wiki (EN/RU), «Рабочий процесс Wan2.2 Animate ComfyUI». Identity can be strengthened with a character LoRA or CLIP Vision reference; FP8 weights suit consumer GPUs — [comfyui-wiki EN](https://comfyui-wiki.com/en/tutorial/advanced/video/wan2.2/wan2-2-animate), [RU](https://comfyui-wiki.com/ru/tutorial/advanced/video/wan2.2/wan2-2-animate).
- RunComfy, "Wan 2.2 Animate: Swap Characters & Lip-Sync Workflow". Inputs are your source clip plus one clean reference image; the hosted medium machine is limited to about 10 s clips — [RunComfy](https://www.runcomfy.com/comfyui-workflows/wan-2-2-animate-swap-characters-lip-sync-workflow-comfyui) ([RU version](https://www.runcomfy.com/ru/comfyui-workflows/wan-2-2-animate-swap-characters-lip-sync-workflow-comfyui)).
- YouTube Wan Animate tutorials (dates n/a unless the title says otherwise):
  - "Wan2.2 Animate ComfyUI Tutorial: Animate & Replace Characters – A Step-by-Step guide for beginners" — [YouTube](https://www.youtube.com/watch?v=j2j6jDr26S4)
  - "WAN 2.2 Animate: Replace Anyone With AI in ComfyUI" — [YouTube](https://www.youtube.com/watch?v=tSaJuj0yQkI)
  - "Wan 2.2 Animate in ComfyUI: Character Replacement Tutorial" — [YouTube](https://www.youtube.com/watch?v=dbG-Hc6dXTA)
  - "Wan 2.2 Animate Head Swap ComfyUI Workflow Walkthrough" (replace only the head) — [YouTube](https://www.youtube.com/watch?v=_a_QVLsBhjg)
  - "WAN 2.2 Animate Tutorial: Character Transfer in ComfyUI (2025)" — [YouTube](https://www.youtube.com/watch?v=AxKt0mm4xlo)
  - "WAN 2.2 Animate – Character Replacement in ComfyUI" — [YouTube](https://www.youtube.com/watch?v=-zJm53J7r9s)
  - "Wan 2.2 Animate on Comfy Cloud: Instant Character Replacement" — [YouTube](https://www.youtube.com/watch?v=AF5SflIp9ok)
  - "Wan 2 2 animate FREE AI Character Swap & Fast Lip Sync Tutorial" — [YouTube](https://www.youtube.com/watch?v=-mbjvCiu6cU)
- A practitioner guide by Nathan Shipley, "Guide: Wan 2.2 Animate – Tips for Control and Quality" (Notion), was found but could not be opened, and no snippet content was returned — [Notion](https://nathanshipley.notion.site/Guide-Wan-2-2-Animate-Tips-for-Control-and-Quality-2a091e11536480108650f538b46cf298).
- Wan-AI's Hugging Face discussion thread has users requesting 2K quality, eyelines, controllable relight and "simple matting for footage" — [Hugging Face](https://huggingface.co/Wan-AI/Wan2.2-Animate-14B/discussions/1).

**(d) Background-only replacement (matting plus AI-generated background)**
- CapCut on PC: Video > Remove Background > **Auto Removal**, then put your talking clip on a higher layer and the background clips below — [Mile High Title Guy blog](https://www.milehightitleguy.com/post/capcut-for-pc-step-by-step-guide-to-editing-talking-head-videos-with-dynamic-backgrounds).
- CapCut's own page: for green or blue backdrops use **Chroma Key** (key colour, intensity, shadow, feather). Best with well-lit footage, strong subject/background contrast and a stable camera — [CapCut](https://www.capcut.com/features/remove-video-background-for-talking-head-videos).
- **Robust Video Matting** in ComfyUI (ComfyUI-Video-Matting) replaces the background with any image or video and uses temporal guidance for consistent mattes — [RunComfy node page](https://runcomfy.com/comfyui-nodes/ComfyUI-Video-Matting/Robust-Video-Matting).
  - An agent skill, "video-bg-replace", mattes a talking head with RVM and composites it over a new background with ffmpeg. It notes that RVM's recurrent memory avoids the flicker of per-image background removers — [skills.sh](https://www.skills.sh/puntorigen/avatar-skills/video-bg-replace).
- SAM2-based matting options:
  - ComfyUI-VideoMaMa: SAM2 video mask generator with foreground/background points — [RunComfy](https://www.runcomfy.com/comfyui-nodes/ComfyUI-VideoMaMa)
  - MatAnyone node — [RunComfy](https://www.runcomfy.com/comfyui-nodes/ComfyUI_MatAnyone_Kytra/mat-anyone-video-matting)
  - Research paper "SAM2Matting" (arXiv 2606.27339, June 2026) — [arXiv](https://arxiv.org/abs/2606.27339)
- A Habr article describes a service with three background modes: "Видео" (place another video behind the subject), "Изображение" (static picture) and "Цвет" (solid colour, e.g. chroma green, for later keying) — [Habr](https://habr.com/ru/news/853572).
- Seedance 2.5 reportedly adds a green-screen / background-replacement mode for existing clips, filmed or generated. This comes from search summaries of X articles about 2.5 and is unconfirmed — [X: TheAIColony, 2026-08-04](https://x.com/TheAIColony/article/2084630768345596145?lang=en).

### Inferences
**Synthesized "how practitioners actually do it" pipeline.** This is my assembly of the findings in all sections, not a single creator's documented recipe.
1. **Shoot A-roll for the model, not for the eye.** Locked-off phone or webcam, frontal or three-quarter face, soft even light facing the speaker, plain uncluttered background (or green screen if you will matte), mouth never covered, slow head motion, a few seconds of stillness at the start and end of each take. Record clean audio separately or keep the camera audio as the master track. (§2)
2. **Cut the A-roll into model-sized chunks at natural pauses:** 3–10 s for Kling, ≤5 s for original Aleph (up to 30 s claimed for Aleph 2.0), 5–15 s for Seedance video refs, 3–30 s for Genjutsu, about 10 s on hosted Wan. Keep each chunk ending on a pause or blink so seams fall on silence. (§3)
3. **Make a "look bible" once.** Restyle one frame (or a clean portrait) per look with an image model and reuse that exact image as the reference or first frame for every chunk of that look. Use one fixed prompt template per look ("keep X unchanged; change only Y"). (§3, §5)
4. **Pick the engine by goal:**
   - Seedance 2.0 Omni reference: strongest character swap and lip-sync, but real-face uploads are banned on official channels, so it is used via verified identity, third-party hosts, or a non-photoreal or AI-styled reference.
   - Aleph 2.0, Kling Omni Edit, Luma Modify or Genjutsu: targeted "edit only the outfit/background" with the original performance kept.
   - Wan Animate Mix: local, uncensored, keeps original sound.
   - Matting plus a generated background plate: background-only changes. This is the safest route for lip-sync because the face pixels are never regenerated.
5. **Keep your voice.** Mute the model's audio and lay the original recorded track back under the cut. If the regenerated mouth drifts, run a lip-sync pass (sync.so lipsync-2-pro or sync-3, or LatentSync) on that chunk against the original audio. (§4)
6. **Assemble in an NLE.** Hard-cut between chunks or looks rather than cross-fading, and cover seams and identity jumps with B-roll, zoom punch-ins or "teleport" cuts. A location or era change per scene turns the seam itself into the format.
7. **Label it.** Realistic altered depictions of a real person need the YouTube "altered or synthetic" toggle, the TikTok AI label and the Meta "AI info" label. Clearly stylized or animated versions are generally exempt on YouTube. (§7)

### Gaps
- I could not open any page or video, so I could not verify step-by-step contents, channel names or upload dates for most YouTube tutorials.
- No Reddit content could be retrieved: the search API blocks reddit.com.
- No Telegram channel posts surfaced in search results for this topic.
- I found no tutorial that explicitly does "my own talking-head A-roll → Seedance 2.0 outfit/era change → original voice kept" with an end-to-end demonstration and timings.
- No English or Russian tutorial was found combining Wan **VACE** with a matted talking head for background generation.

## 2. What shooting guidelines do practitioners recommend?

### Takeaway
Shoot a stable, well-lit, frontal, uncluttered take with the mouth always visible, slow and simple movement, and consistent lighting across takes. Avoid long occlusions (hands, mic, hair) and sudden head turns or profiles. Short test clips (5–10 s) come before committing to a long video.

### Cited Findings
- Plain or minimal background (blank wall, green screen, cyclorama) makes style transfer more consistent; face a natural light source rather than backlighting; prefer stable footage to shaky handheld — [Kolbo: Video-to-Video AI guide](https://kolbo.ai/blog/video-to-video-ai-guide); [Pippit style transfer](https://www.pippit.ai/tools/video-style-transfer); [Morphic: How to make AI video look real](https://morphic.com/resources/how-to/how-to-make-ai-video-look-real) *(the summary blended these sources; exact attribution per tip not verifiable)*.
- Snapchat Easy Lens tutorial: plan a short, simple action (a head turn, a walk toward camera, a wave). Clear, slow movement survives restyling better than fast movement — [Easy Lens](https://easylens.snapchat.com/learn/tutorials/restyle-a-video-with-ai).
- MindStudio: in video-to-video style transfer the source video drives "head position, blinks, mouth shapes, gaze, shoulder motion" — [MindStudio](https://www.mindstudio.ai/blog/gpt-6-astra-animated-video-style-transfer).
- In prompts, ask the model to keep your recognizable features, otherwise models "smooth people out" or make them "prettier" — [Kolbo](https://kolbo.ai/blog/video-to-video-ai-guide) *(attribution within the search summary uncertain)*.
- Runway/Aleph: stable-camera, well-lit clips work best. Strong shakes, motion blur, poor lighting and big structural changes reduce tracking reliability — [Framia](https://framia.converge.ai/page/en-US/blog/how-to-use-runway-aleph-2); [seedance.tv Aleph 2 prompt guide](https://www.seedance.tv/es/blog/runway-aleph-2-prompt-guide).
- Luma Modify: blurry, low-res or noisy footage degrades motion-capture accuracy; cluttered or fast-moving backgrounds cause artifacts — [Cliprise Luma Modify Ray3 guide](https://www.cliprise.app/learn/guides/model-guides/luma-modify-ray3-complete-guide-2026).
- Wan Animate driving footage:
  - Avoid heavy occlusions covering the face for long periods.
  - Prefer clips with fewer sudden head turns or fast occlusions.
  - Exaggerated, clear expressions drive better than micro-expressions.
  - Use a sharp, front-facing or three-quarter reference with neutral expression and even lighting.
  - Use at least 720p for output, 480p for tests, and 3–5 s driving clips for fast motion.
  - [Wan Animate guides: wananimate.app](https://wananimate.app/character-animation-replacement); [wan-animate.com](https://wan-animate.com/posts/wan-2-2-animate-motion-types-style-consistency-guide); [Atlabs](https://www.atlabs.ai/blog/wan-2-2-animate-guide) *(secondary SaaS guides)*
- Seedance reference portraits: remove the background (transparent PNG); keep face edges, even lighting and the **mouth** visible. Seedance models mouth shapes from the portrait, so blurry or occluded faces hurt lip-sync — [Cutout.pro Seedance audio guide](https://www.cutout.pro/learn/?p=2903).
- Seedance identity across shots:
  - Changing the side light makes it "already a slightly different person", so keep lighting identical; upload up to 4 photos of the same face from different angles — Russian-language guide surfaced with [vc.ru Prompt Studio](https://vc.ru/promtstudio/2919129-seedance-2-0-gayid-po-video-neyroseti-bytedance) *(exact source page within results not isolated)*.
  - Multiple inconsistent reference images with different lighting get averaged, which causes face morphing; use fewer, consistent references — [Magic Hour](https://magichour.ai/blog/how-to-use-seedance-20).
- Record a few extra seconds of stillness on camera so you have a clean endpoint frame for an AI transition clip (Runway keyframe mode) — [MindStudio: AI video transitions between locations](https://www.mindstudio.ai/blog/ai-video-transitions-locations-runway-seedance).
- Lip-sync tools need visible mouths:
  - Sync.so: hands, microphones, hair or sunglasses over the mouth degrade lipsync-2/-2-pro, and extreme profile shots make face detection unreliable — [sync.so docs](https://sync.so/docs/compatibility-and-tips/improving-lip-sync-quality).
  - LatentSync wants a clear front-facing face, 25 fps, a single face and ≤1080p — [RunComfy LatentSync](https://www.runcomfy.com/comfyui-workflows/latentsync-advanced-lip-sync-video-generator).
- First-frame quality: video generators tend to preserve the first frame's colour histogram, so an underexposed first frame carries shadow noise into the whole clip — [Nerdbot, 2026-04-27](https://nerdbot.com/2026/04/27/rethinking-first-frame-quality-through-nano-banana/).
- Kling Omni Edit input spec: 3–10 s, 720p–2160p, 24–60 fps — [Media.io](https://www.media.io/ai/video-edit/kling-ai-video-editor). Wan Animate dimensions must be multiples of 16 — [comfy.org](https://comfy.org/workflows/video_wan2_2_14B_animate-c2c4b45b7df5/). LatentSync prefers 25 fps — [RunComfy](https://www.runcomfy.com/comfyui-workflows/latentsync-advanced-lip-sync-video-generator).

### Inferences
- A practical checklist that reconciles all tools: 1080p, 25 fps, locked-off camera at eye level, chest-up framing with headroom (leaves room for outfit changes to read), soft key light in front, the same light setup for every session, plain wall or green screen, no hands crossing the face, no mic in front of the mouth (use a lav), no profile turns, pause and blink between sentences (cut points), and identical wardrobe in all takes (gives the model a stable base to repaint).
- Shooting on green or plain backgrounds helps both routes. It makes matting trivial, and it reduces "background hallucination" bleed in full video-to-video edits.

### Gaps
- No primary-source practitioner checklist (e.g., from a named creator's video) could be verified. The tips come from secondary guides and vendor docs.
- No source quantified the impact of hand gestures in front of the face specifically for Seedance, Aleph or Kling restyles.

## 3. How do creators handle videos longer than one generation (chunking, consistency, hiding seams)?

### Takeaway
Every engine caps the input or output at roughly 3–30 s, so long talking-head videos are always split into short segments. Consistency comes from reusing the same reference image(s), the same prompt template and identical lighting per look. I found no documented, tested method for seamless chaining across chunk boundaries; creators lean on hard cuts and format choices ("teleport" per scene, era change per segment) that make seams intentional.

### Cited Findings
- Per-generation length limits reported:
  - Original Runway Aleph: **5 s per generation**; split longer footage into 5 s segments with the **same prompt** — [Cliprise Aleph guide](https://www.cliprise.app/learn/guides/model-guides/runway-aleph-complete-guide); [Flora docs](https://docs.florafauna.ai/models/video-models/runway-aleph-by-runway).
  - Aleph 2.0: a review states edits of up to **30 s at 1080p**; sources conflict and the limit may depend on version — [Coverr Aleph 2.0](https://coverr.co/tools/runway-aleph-2-0) *(attribution among search hits uncertain)*.
  - Kling Omni/O1 edit: input 3–10 s; VEED returns a 10 s edited video — [Media.io](https://www.media.io/ai/video-edit/kling-ai-video-editor); [VEED Kling O1 vid2vid](https://veed.io/ai-models/video-to-video/kling-o1-vid2vid).
  - Seedance 2.0 video references: one Russian guide says 5–15 s and ≤10 MB; another says up to 3 clips of ≤50 MB and ≤15 s each (conflicting) — [vc.ru Prompt Studio advanced guide](https://vc.ru/ai/2919130-seedance-2-0-prodvinutyi-gayd). Output up to 15 s — [Morphic](https://morphic.com/resources/how-to/seedance-guide).
  - Higgsfield Genjutsu: 3–30 s — [Higgsfield](https://higgsfield.ai/genjutsu).
  - Hosted Wan Animate (RunComfy medium machine): about 10 s — [RunComfy](https://www.runcomfy.com/comfyui-workflows/wan-2-2-animate-swap-characters-lip-sync-workflow-comfyui).
  - Seedance 2.5 (out by Aug 2026) does about 30 s per prompt with sound — [X: OpenGradient article, 2026-08-10](https://x.com/OpenGradient/article/2086781046239224025); see also [X: Min Choi, "I spent a few days with Seedance 2.5", 2026-08-06](https://x.com/minchoi/article/2085502664092066178).
- Seedance reference limits: up to **9 images, 3 videos, 3 audio clips** per generation — [vc.ru Prompt Studio](https://vc.ru/promtstudio/2919129-seedance-2-0-gayid-po-video-neyroseti-bytedance); [Magic Hour](https://magichour.ai/blog/how-to-use-seedance-20).
- In Seedance, the "References" and "First and last frame" modes cannot be used at the same time, and the model can sometimes mix the hero's clothing with the costume reference — [dsgners.ru](https://dsgners.ru/yelpin/42655-seedance-2-0-polnyiy-gayd-po-rabote-s-neyrosetyu-15-promptov) / [vc.ru](https://vc.ru/ai/2868890-seedance-2-0-vozmozhnosti-generatsii-video) *(summary blended these)*.
- First-frame restyling with an image model (Nano Banana) is used to build a "master scene" that is then varied, keeping composition fixed — [Nerdbot](https://nerdbot.com/2026/04/27/rethinking-first-frame-quality-through-nano-banana/).
  - Storyboard guidance: 8–14 keyframes for a 30–45 s short and 15–25 for 1–2 min, each keyframe used as a video start frame — [Apiyi Nano Banana Pro storyboard guide](https://help.apiyi.com/en/nano-banana-pro-ai-video-storyboard-character-consistency-guide-en.html).
- Luma Ray3 Modify's **Character Reference** locks likeness, costume and identity across a clip, and Start/End frames constrain continuity — [YourStory, 2025-12-18](https://yourstory.com/ai-story/luma-ai-ray3-modify).
- Location transitions:
  - Failure modes are a jarring jump when lighting or framing differs too much between locations, and identity drift mid-transition.
  - Fixes are image-to-video from a strong start image and Runway keyframe mode (start image plus last frame).
  - [MindStudio](https://www.mindstudio.ai/blog/ai-video-transitions-locations-runway-seedance)
- A known failure mode in AI history video: "the subject's face morph[s], the period-accurate clothing transform[s] into modern attire". Reference-image workflows are meant to prevent this — [Atlas Cloud Seedance 2.5 history/education guide](https://www.atlascloud.ai/blog/tips/seedance-2.5-ai-video-education-history).
- For lip-sync passes on long-form content, sync.so recommends splitting video into segments **under 2 minutes**. Quality degrades where chunk boundaries fall on partially visible or fast-moving faces — [sync.so docs](https://sync.so/docs/compatibility-and-tips/improving-lip-sync-quality).
- Wan Animate: keep FPS matched and pose alignment and mask quality correct; the result "is not one Generate button" — [aireiter (RU)](https://aireiter.com/ru/blog/wan2-2-animate-guide).

### Inferences
- The dominant practical pattern is: one look = one reference image + one prompt template + identical lighting, applied to N sequential 5–15 s chunks cut on pauses, then reassembled with the **original continuous audio** underneath. Because the audio is continuous, small visual discontinuities at hard cuts read as normal jump cuts in talking-head grammar.
- The "teleport per scene" and "different era costume per segment" formats are partly a response to chunking limits. When each chunk deliberately has a different look, the viewer expects a discontinuity, so seams cost nothing.
- Seedance 2.5's roughly 30 s single generation (Aug 2026) roughly halves the number of chunks versus 2.0's 15 s. That reduces seams but not the real-face policy issue.

### Gaps
- No source documented fixed-seed practice for Seedance, Kling or Aleph (seeds are often not exposed in these UIs). I found no evidence either way.
- No source tested last-frame-to-next-chunk chaining for talking heads, or measured identity drift across chunks.
- No creator-reported chunk count or edit-decision structure for a real 1–5 minute restyled talking-head video was found.

## 4. How do creators keep or restore lip-sync (original audio vs re-sync pass)?

### Takeaway
There are two strategies:
1. **Keep the original performance and audio.** Video-edit modes (Kling keep_audio, Wan Animate Mix, Aleph/Luma edits, matting) regenerate the image but follow the real mouth motion, and creators re-lay the original audio track.
2. **Regenerate and re-sync.** Seedance with an audio or "black-screen video" reference, or a dedicated lip-sync pass (sync.so lipsync-2-pro/sync-3, LatentSync, HeyGen).

Aleph is reported to give only general facial movement, not precise lip-sync.

### Cited Findings
- Kling O1 Video Edit can preserve the original audio "if desired" via a platform parameter — [MuAPI Kling O1 Video Edit](https://muapi.ai/playground/kling-o1-video-edit); [MuAPI Kling O1 Standard](https://muapi.ai/playground/kling-o1-standard-video-edit). Kling 3.0 Omni Edit API exposes **keep_audio** — [Unifically](https://unifically.com/models/kling-3.0-omni-edit).
- Wan Animate **Mix** mode keeps the original scene, background and sound — [seedance.tv Wan Animate 2 tutorial](https://www.seedance.tv/blog/wan-animate-2-tutorial).
- Runway Aleph: a third-party model page lists "general facial movement, not precise lip-sync" as a limitation — [Coverr Aleph 2.0](https://coverr.co/ai/models/runway-aleph-2-0) *(attribution among search hits uncertain)*.
- Seedance audio handling:
  - A reference video's own audio overrides a separately tagged audio file — [OpenArt](https://openart.ai/blog/seedance-2-0-handbook/).
  - Directly uploaded audio can be altered; a blank video carrying the audio works better — [X: Travis Davids, 2026-04-16](https://x.com/MrDavids1/status/2044600846416068714).
  - Audio references may drift in rhythm, so convert segments to black-screen MP4 references — [Seegen](https://seegen.ai/seedance-2-0-audio-guide).
  - Use a 5–15 s dialogue voice reference and instruct the model to "use the voice and timing from @Audio1" — X search summary tied to [GumVue, 2026-06-16](https://x.com/GumVue/article/2066700181161001277) *(attribution uncertain)*.
- Curious Refuge: Seedance 2.0 was best in their live-action lip-sync tests — [Curious Refuge](https://curiousrefuge.com/blog/ai-lip-sync-workflows); [X, 2026-05-05](https://x.com/CuriousRefuge/status/2051768714224414749).
- Another guide warns that without a real mouth close-up and talking reference, Seedance invents its own mouth shapes, and that tight word-level lip-sync may need a dedicated lip-sync pass — [Seedance.tv talking head (2.5)](https://www.seedance.tv/blog/seedance-2-5-talking-head-video-2026); [Sagnik Bhattacharya: How to Create Lip-Sync and Talking-Head Videos in Seedance (2026)](https://sagnikbhattacharya.com/blog/seedance-2-lip-sync-talking-head) *(summary blended sources)*.
- Fallback: refine timing in CapCut, or composite the background separately — X search summary *(no single attributable post)*.
- Sync.so lipsync-2 / lipsync-2-pro / sync-3:
  - Processes in **2 s chunks**; segments with still frames won't sync.
  - `occlusion_detection_enabled` helps with hands or mics but is slower; sync-3 handles obstructions automatically.
  - `sync_mode` cut_off (default), loop or bounce handles audio/video length mismatch.
  - Split long-form into chunks under 2 min.
  - [sync.so tips](https://sync.so/docs/compatibility-and-tips/improving-lip-sync-quality); [sync.so models](https://sync.so/docs/models/lipsync); [Replicate sync/lipsync-2-pro](https://replicate.com/sync/lipsync-2-pro); [WaveSpeed lipsync-2-pro](https://wavespeed.ai/models/sync/lipsync-2-pro).
- LatentSync (ByteDance, open source) in ComfyUI:
  - Wants a clear frontal face, 25 fps, one face, ≤1080p.
  - Fix "Face not detected" by setting the frame load cap under 150 and keeping clips under 1 min.
  - [GitHub](https://github.com/bytedance/LatentSync); [RunComfy](https://www.runcomfy.com/comfyui-workflows/latentsync-advanced-lip-sync-video-generator); [ThinkDiffusion](https://learn.thinkdiffusion.com/seamless-lip-sync-create-stunning-videos-with-latentsync/).
- Consistent synthetic voice across generations, if not using your own track:
  - ElevenLabs custom voice trick for Kling 3.0 / Seedance — [YouTube](https://www.youtube.com/watch?v=b9uvXLvWL08)
  - Seedance voice consistency tutorial — [YouTube](https://www.youtube.com/watch?v=lOa3oiUal-M)

### Inferences
- For a creator who wants **their own voice**, the lowest-risk order is:
  1. Background-only via matting. Face pixels are untouched, so lip-sync is perfect.
  2. Edit modes that track the real mouth (Kling keep_audio, Wan Mix, Luma Modify).
  3. Full regeneration (Seedance) with the original audio as a black-screen video reference.
  4. A sync.so or LatentSync pass on any chunk where the mouth drifts.

  Always mute the model's audio and re-lay the original WAV in the edit.
- Seedance "voice" features are mainly useful for AI characters. For a real creator, the original recorded track should be the master and the model only needs to match it.

### Gaps
- No source measured lip-sync accuracy (e.g., LSE-C/LSE-D) for restyled real talking heads across Seedance, Kling, Aleph or Wan.
- No source confirmed whether Kling Omni Edit or Aleph 2.0 keep exact mouth shapes after an outfit change, or only plausible motion.

## 5. Prompt patterns for "keep face, expression and mouth exactly; change only outfit/background"

### Takeaway
The consistent pattern across tools is a **preserve-first, single-change** prompt:
1. Start with an edit verb.
2. Name the one target element and its new state.
3. Explicitly list what must stay unchanged (face, expression, mouth and lip movement, camera, timing, background or outfit).
4. In Seedance and Kling, bind uploaded files with @-tags (@Video1 = performance, @Image1 = face, outfit or location).

### Cited Findings
- Aleph prompting:
  - Start with a direct edit verb, name the target element and desired result, then state what must stay unchanged. Aleph works best for targeted edits, not completely different compositions — [seedance.tv Aleph 2 prompt guide](https://www.seedance.tv/es/blog/runway-aleph-2-prompt-guide).
  - Official example: "Change the outfit and bag to soft yellow." — [Runway Help](https://help.runwayml.com/hc/en-us/articles/52150503729171-Aleph-2-0-Prompting-Guide).
  - One edit per generation; chain edits — [Framia](https://framia.converge.ai/page/en-US/blog/how-to-use-runway-aleph-2).
- Kling O1 video edit: state up front what remains unchanged (camera movement, subject blocking, background elements), then the single change — [fal Kling O1 prompt guide](https://fal.ai/learn/devs/kling-o1-prompt-guide).
- Kling 3.0 Omni syntax: "Change [describe specified subject] in [@Video] to [@Image]" — [Media.io](https://www.media.io/ai/video-edit/kling-ai-video-editor).
- Seedance background-only example (from Seedance 2.5 material): "keep the original character movements and camera tracking speed unchanged; modify only the background" — Russian search summary of Seedance guides *(exact page not isolated; nearest: [vc.ru Prompt Studio advanced guide](https://vc.ru/ai/2919130-seedance-2-0-prodvinutyi-gayd))*.
- Seedance:
  - Explicitly reference @image1; otherwise the photo is treated as "inspiration" — [vc.ru advanced guide](https://vc.ru/ai/2919130-seedance-2-0-prodvinutyi-gayd).
  - Use "@Image1 for exact facial features" when the face drifts — [Magic Hour](https://magichour.ai/blog/how-to-use-seedance-20).
  - Pin the face with a separate instruction when changing clothes — [dsgners.ru](https://dsgners.ru/yelpin/42655-seedance-2-0-polnyiy-gayd-po-rabote-s-neyrosetyu-15-promptov).
  - Clothes-swap remix: replace the clothes of the person in @Video1 with the clothes from @Image1 — [vc.ru full guide](https://vc.ru/ai/2748739-seedance-2-0-polnoe-rukovodstvo).
  - For character swap: video as OMNI Reference + character image, "keep the scene the same" — [X: Travis Davids](https://x.com/MrDavids1/status/2043891653346283606).
  - Image refs for clothing styles + video ref for rhythm — [WaveSpeed](https://wavespeed.ai/blog/posts/seedance-2-0-complete-guide-multimodal-video-creation/).
  - Name one speaker and quote one short line; start with a short shot — [Seeddance.io lip-sync guide](https://www.seeddance.io/blog/seedance-ai-lip-sync-guide) *(attribution uncertain among results)*.
- Community-recommended Seedance reference mix: **one face reference, one style reference, one audio reference** — [seeddance2.app "Reddit tutorial" summary](https://seeddance2.app/blog/seedance-2-0-tutorial-reddit) *(secondary summary of Reddit, not Reddit itself)*.
- Luma Modify: steer with visual references, first-frame images or prompts; edit single elements (wardrobe, sky) without changing the whole shot — [Luma](https://lumalabs.ai/news/introducing-modify-video).

### Inferences
Template that combines the above (my synthesis, not a quoted prompt):

> "Edit @Video1. Keep the person's face, identity, facial expressions, eye-line, head motion and **mouth/lip movements exactly as in @Video1**; keep camera framing and timing unchanged. Change **only** [the outfit → 1890s Victorian frock coat as in @Image2] / [the background → a sunlit Roman forum as in @Image3]. Match lighting direction to the original. No text, no extra people."

Practitioners add negative or guard phrases such as "do not beautify / do not alter face shape", following the Kolbo note that models "prettify" by default. Change outfit **or** background per pass, not both, following Aleph's one-edit rule.

### Gaps
- No A/B evidence on which guard phrases measurably improve mouth fidelity.
- No verified Russian-language prompt library dedicated to talking-head restyles was found.

## 6. Typical cost and turnaround per minute of finished video; common pitfalls and complaints

### Takeaway
At list prices, regenerating one minute of 720p footage costs roughly **$9–$17** on Seedance 2.0 (official BytePlus) or Runway Aleph 2.0, before re-rolls. Real-world spend is typically several times that because of retries; matting-only background swaps are nearly free. Turnaround is minutes per 5–10 s clip (Seedance 10 s ≈ 3–5 min; local Wan 720p ≈ 4–9 min per 5 s on an RTX 4090). The biggest pitfall for this trend is **Seedance 2.0's real-human-face upload ban** on official channels.

### Cited Findings
- Seedance 2.0 official BytePlus API pricing:
  - About **$0.07/s (480p), $0.15/s (720p), $0.37/s (1080p), $0.78/s (4K)**; Fast and Mini are cheaper.
  - Example: a 5 s 720p clip with a reference video costs $0.84.
  - Activation requires a prepaid resource pack.
  - [Framesurfer, Sept 2026](https://framesurfer.com/blogs/seedance-2-0-pricing); [Anikuku](https://anikuku.com/blog/seedance-2-api-pricing-guide-2026); [BytePlus ModelArk docs](https://docs.byteplus.com/docs/ModelArk/2291680)
- Volcengine (China): about ¥1 per second; video-input editing is priced lower per token than pure generation — [aicost.org](https://aicost.org/blog/seedance-2-0-api-pricing-breakdown-2026). This conflicts with a Russian summary claiming edit mode costs about 1.5× more on one service (source page not isolated).
- Reseller tiers are as low as $0.022/s (Atlas Cloud Fast), with reliability caveats — [Atlas Cloud](https://www.atlascloud.ai/blog/case-studies/seedance-2.0-pricing-full-cost-breakdown-2026). Runway's Seedance 2.0 API: $0.36/s at 720p; Seedance 2.5: $0.30/s — [Camclo3d](https://camclo3d.com/blog/seedance-pricing). See also [Cutout.pro "Real Monthly Cost After Testing 200+ Clips"](https://www.cutout.pro/learn/blog-seedance-2-0-pricing/) and [OpenRouter](https://openrouter.ai/bytedance/seedance-2.0).
- Runway Aleph 2.0 is listed at **28 credits/second** (280 credits per 10 s), checked against Runway's pricing in Aug 2026. Developer API credits cost $0.01 each, which works out to about $0.28/s (my arithmetic) — [Creatify Runway pricing 2026](https://creatify.ai/blog/runway-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay).
- Kling O1 / 3.0 Omni Edit pricing: not found.
- Turnaround:
  - Seedance 2.0 10 s clip took **3–5 minutes**; realistic human faces "get blocked often" — [DEV Community](https://dev.to/dishant0406/seedance-20-hype-hollywood-panic-and-the-real-story-579p).
  - Wan 2.2 base A14B 720p on an RTX 4090: I2V about 4m15s, T2V about 5m30s ([Apatero, marketing-ish](https://apatero.com/blog/ai-video-generation-speed-benchmarks-2025)). TI2V-5B 5 s 720p about 9 min ([Evetech](https://evezone.evetech.co.za/deep-dives/local-ai-video-generation-hardware-hub-gpus-for-ltx-2-and-wan-2-2-in-south-africa)).
  - Wan Animate 480p in about 10–15 min on an RTX 4050 6 GB — [TheLocalLab Patreon](https://www.patreon.com/TheLocalLab/posts/wan-2-2-animate-139973446). About 24 GB VRAM is recommended for Wan Animate — [lilys.ai (ES)](https://lilys.ai/es/notes/comfyui-20251214/wan-animate-ai-character-swap-lip-sync).
- **Real-face ban (Seedance 2.0):**
  - Dreamina lists Seedance 2.0 / 2.0 Fast / 2.0 Mini with "Real human faces are not supported" and rejects uploads with "face detected".
  - BytePlus API docs: the 2.0 series "do not support direct upload of reference images or videos containing real human faces".
  - ByteDance's launch post: real human portraits as subject references require "identity verification or prior legal authorization".
  - [Seedrouter](https://seedrouter.ai/blog/seedance-real-person-error); [Reapi](https://reapi.ai/blog/seedance-not-eligible-explained); [Ruoqijin](https://ruoqijin.com/blog/seedance-access-and-face-policy); [Phemex news: relaunch with real-face upload ban](https://phemex.com/news/article/bytedance-relaunches-seedance-20-globally-with-restrictions-on-realface-uploads-68605)
  - One third-party blog claims the block applies even to your own face with no toggle — [Vicsee](https://vicsee.com/blog/seedance-2-0-face-workaround).
  - Some third-party hosts are looser; Kittl advertises "bring your own human reference" — [Kittl via search](https://www.kittl.com/blogs/?p=24205); [MindStudio on restrictions](https://www.mindstudio.ai/blog/seedance-2-0-content-restrictions-workarounds).
- Access from Russia: foreign AI aggregators are unavailable from Russian IPs (per vc.ru) — [vc.ru](https://vc.ru/ai/2868890-seedance-2-0-vozmozhnosti-generatsii-video); Russian access guides — [Habr](https://habr.com/ru/companies/study_ai/articles/1044872/), [RBC Trends](https://trends.rbc.ru/trends/social/69b735739a7947933706ce64).
- Other complaints and pitfalls:
  - Face morphing from inconsistent references — [Magic Hour](https://magichour.ai/blog/how-to-use-seedance-20).
  - Costume bleed (hero's clothing mixed with the reference costume) — [dsgners.ru](https://dsgners.ru/yelpin/42655-seedance-2-0-polnyiy-gayd-po-rabote-s-neyrosetyu-15-promptov).
  - Period clothing drifting to modern attire — [Atlas Cloud](https://www.atlascloud.ai/blog/tips/seedance-2.5-ai-video-education-history).
  - Lighting or framing jumps between locations — [MindStudio](https://www.mindstudio.ai/blog/ai-video-transitions-locations-runway-seedance).
  - Aleph's imprecise lip-sync — [Coverr](https://coverr.co/ai/models/runway-aleph-2-0).
  - "Most beginner tutorials overpromise; expect mouth and face artifacts" — [Sagnik Bhattacharya](https://sagnikbhattacharya.com/blog/seedance-2-lip-sync-talking-head) *(per search summary)*.

### Inferences
- Cost per finished minute (my arithmetic from the list prices above):
  - Seedance 2.0 720p official: 60 s × $0.15 ≈ **$9 per pass**.
  - Aleph 2.0: 60 × $0.28 ≈ **$17 per pass**.
  - With a typical 2–4× re-roll factor and a lip-sync pass, a realistic budget is roughly **$20–$70 per finished minute** on hosted models.
  - Local Wan Animate costs only electricity but needs a 24 GB GPU and about 1–2 h of rendering per finished minute at 720p.
  - Matting plus a generated background plate needs only one 5–10 s background generation per location, so it is the cheapest.
- Turnaround per finished minute: about 6–12 chunks × 3–5 min of generation, plus retries, lip-sync and editing. That is plausibly **1–3 hours of wall-clock time** for a hosted pipeline (inference, no direct creator report found).
- Because of the real-face ban, a "film myself → Seedance restyle" workflow on official ByteDance surfaces requires identity verification. Otherwise the video is pushed toward Kling, Aleph, Luma, Wan or third-party Seedance hosts. This is likely why many visible "Seedance talking head" successes use AI-generated or stylized characters.

### Gaps
- No creator-reported end-to-end time or cost for a real 1–5 min restyled talking-head video.
- Kling Omni Edit pricing, Luma Modify credit costs and Higgsfield Genjutsu credit costs were not found.
- I could not find the exact identity-verification procedure for using your own face in Seedance 2.0 on Dreamina or BytePlus.

## 7. Example channels/accounts and audience reaction / disclosure norms

### Takeaway
The best-documented viral example of the Seedance "talk to camera, travel through history" format is **Chloe vs History**, run by Jonathan Laramy (Majestic Studios), launched Feb 2026. However, Chloe is a **fully AI-generated** presenter, not a filmed creator. I found no verified named channel that films a real host and restyles them per era or location.

Disclosure rules:
- **YouTube:** realistic altered or synthetic depictions of real people must be disclosed. Clearly unrealistic, animated or special-effects content is exempt. Since May 2026 YouTube auto-labels significant photorealistic AI use.
- **TikTok:** requires labels on realistic AI depictions of people.
- **Meta:** applies "AI info" automatically or manually.

Studies show labels cost a few percent of engagement, while hidden-then-detected AI is penalized more.

### Cited Findings
- Chloe vs History: created by British social media strategist **Jonathan Laramy**, who also runs AI history channel Majestic Studios.
  - Chloe is fully AI-generated and addresses camera in 9:16 clips, then "travels" to historical scenes (e.g., Marie Antoinette).
  - Video is made with Seedance 2.0 and scripts with Claude.
  - Launched the same month Seedance 2.0 shipped (Feb 2026).
  - [Choosely](https://choosely.ai/ai-radar/chloe-vs-history-ai-stack)
- Dreamina markets an "AI History Generator" (Seedance) for "videos of a past no one filmed" — [Dreamina](https://dreamina.capcut.com/seedance/ai-history-generator). Atlas Cloud has a Seedance 2.5 guide for historical and educational content — [Atlas Cloud](https://www.atlascloud.ai/blog/tips/seedance-2.5-ai-video-education-history).
- Other AI-video creator accounts active on this toolset (tutorial and test posters, not talking-head explainers):
  - Travis Davids — [X](https://x.com/MrDavids1/status/2043891653346283606)
  - Curious Refuge — [X](https://x.com/CuriousRefuge/status/2051768714224414749)
  - Min Choi — [X](https://x.com/minchoi/article/2085502664092066178)
  - Amira Zairi (@azed_ai): Seedance 2.0 on Freepik, 2026-04-10 — [X](https://x.com/azed_ai/status/2042602819656798356)
  - APOB AI: "The Viral AI Video Playbook… Seedance 2.5", 2026-09-19 — [X](https://x.com/apob_ai/article/2101183296751505857)
- YouTube disclosure:
  - Must disclose realistic altered or synthetic content a viewer could mistake for a real person, place or event. Examples include digitally replacing one person's face with another and synthetically generating a person's voice.
  - Not required for clearly unrealistic or animated content, special effects such as background blur and beauty filters, or production assistance.
  - [AIR Media-Tech](https://air.io/en/youtube-glossary/what-is-youtubes-ai-content-disclosure-policy); [TechSpot](https://www.techspot.com/community/topics/youtube-introduces-labeling-requirements-for-synthetic-and-altered-content.284923/); [Minimatters](https://minimatters.com/youtube-altered-or-synthetic-content-disclosure/)
- May 2026 YouTube update:
  - If a creator doesn't specify but systems detect significant photorealistic AI use, YouTube "will now automatically apply a label". Creators can dispute it in YouTube Studio. Labels are moving to more visible spots.
  - [Minimatters May 2026](https://minimatters.com/youtube-ai-content-labeling-update-in-may-2026/); [PPC Land](https://ppc.land/youtube-shifts-generative-ai-labels-to-spots-viewers-will-actually-see/); [eMarketer](https://www.emarketer.com/content/automatic-ai-labels-youtube-test-creator-advertiser-trust)
  - Sources conflict on when the requirement formally took effect: the Studio toggle launched March 2024 per one source, versus "formal effect May 21, 2025" per another.
- TikTok and Meta disclosure:
  - TikTok requires labeling realistic AI-generated images, audio or video of people via an upload toggle, and integrated C2PA Content Credentials in Jan 2025. One source claims non-labeling now draws an immediate strike (unconfirmed) — [Storrito](https://storrito.com/resources/tiktoks-2026-ai-labeling-rules-and-what-they-signal-for-platform-governance); [Social Media Today](https://www.socialmediatoday.com/news/tiktok-officially-launches-new-in-stream-labels-for-ai-generated-content/694154/).
  - Meta applies "AI info" automatically on detection or manually via advanced settings. For content only *edited* with AI the label can sit in the post menu, while AI-*generated* content is labelled more prominently — [Metricool](https://metricool.com/how-to-label-ai-content/).
  - A claimed May 2026 Instagram profile-level "AI creator" label appears in one source only (unconfirmed) — [Metricool](https://metricool.com/how-to-label-ai-content/).
- Audience reaction:
  - A JCR study reported about **7–8% fewer likes** on TikTok posts with AI disclosure (eight preregistered experiments). Other studies found no significant change.
  - Ipsos: 79% across 30 countries want AI disclosure.
  - [Sherlock Comms summary](https://sherlockcomms.com/?p=78985)
  - A 2026 study of 787 TikTok videos from 30 creators found that inauthenticity reduced likes and shares, and an AI label softened that penalty — [Hawaii ScholarSpace (HICSS)](https://scholarspace.manoa.hawaii.edu/collections/cd2f296d-fcd8-42b1-88cb-e501e1ff7a88).
  - A theory paper models a penalty for hidden AI use that is later detected — [arXiv 2601.18654](https://arxiv.org/pdf/2601.18654).
  - Kapwing aggregates disclosure and trust stats — [Kapwing](https://www.kapwing.com/resources/55-ai-generated-video-statistics-disclosure-detection-and-trust/).

### Inferences
- For a real creator restyling themselves:
  - A **photoreal** outfit, era or location change of a real person in a "real-looking" place falls under YouTube's "altered/synthetic" disclosure.
  - A clearly **stylized or animated** version (anime, clay, painterly) plausibly falls under the "clearly unrealistic/animated" exemption.
  - A background-only swap of a studio shot is borderline. YouTube exempts background blur, but a photoreal fake location could mislead about "place".
  - Given YouTube's May 2026 auto-labelling, self-disclosing is the safer default.
- An on-screen acknowledgment ("this is me, AI-restyled; my real voice") matches the pattern that disclosed, high-quality AI content suffers less trust loss than discovered non-disclosure.

### Gaps
- No verified real-host educational, history or science-pop channel using the "film yourself → AI costume/location per segment" format was found. Neither English nor Russian searches surfaced named examples, and Telegram and Reddit were not reachable.
- I could not access YouTube's, TikTok's or Meta's own help-center pages (fetch blocked). Platform rules above come from secondary coverage and should be checked against official help pages.
- I found no audience-reaction data specific to AI-restyled *real* talking heads, as opposed to AI content generally.
