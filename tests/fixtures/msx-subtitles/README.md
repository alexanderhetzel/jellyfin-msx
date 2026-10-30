# Public synthetic subtitle research

Independently authored UTF-8 German/English cues and an independently generated
media remux. No operator media, credentials, private grants or proprietary MSX
runtime code. These assets are excluded from wheel/container packages by the
existing package allowlists. Only official vendor-hosted MSX/HTML5X code is used.

`embedded.mp4` copies the video/audio packets of `../msx-public/synthetic.mp4`
(provenance there) and adds `de.srt` as MP4 `mov_text`, absolute stream index 2,
subtitle ordinal 0, language `deu`, default disposition. FFmpeg 7.1 from the
previously installed `imageio-ffmpeg==0.6.0` PyPI wheel was used locally:

```sh
ffmpeg -hide_banner -loglevel error -n -i tests/fixtures/msx-public/synthetic.mp4 \
  -i tests/fixtures/msx-subtitles/de.srt -map 0:v:0 -map 0:a:0 -map 1:0 \
  -c:v copy -c:a copy -c:s mov_text -metadata:s:s:0 language=deu \
  -metadata:s:s:0 'title=Synthetic German index 2' -disposition:s:0 default \
  -movflags +faststart tests/fixtures/msx-subtitles/embedded.mp4
```

Source revision: `d0c6fe2ab74f643756f9d7ea8119298b238d8f2f`; source SHA256:
`44f03da6c498584f27f5f04471935dc2ec5931769e28fbaf7c0a91fcff8fc406`.
Result SHA256: `5d01d1499ad049ea72cc2ef98a068a2059442a91aed7a27646f6bf8bee76b5ca`.
Result size: 4,132,257 bytes.
Video/audio are unchanged H.264 Main/yuv420p/1280x720/24 fps and AAC stereo/48 kHz,
30 seconds. No video/audio encoding or Ultra request occurred. SRT/ASS are raw
negative probes; a listed menu track is not a successful subtitle render.

`tools/public_subtitle_fixture.py` generates the public matrix from a known
public HTTPS asset base. Its validator is not a private-URL sanitizer; never
give it a private origin. Subtitle CORS stays explicitly enabled: the official
HTML5X online proxy mode is prohibited for private content. `missing.vtt` is
deliberately absent. Browser evidence and delivery decision belong in
`docs/msx-subtitle-research.md`; physical Philips comparison belongs in #4.
