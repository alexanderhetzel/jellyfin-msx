# Public synthetic MSX renderer/player assets

The MP4 is independently generated test-pattern video and a quiet 440 Hz tone,
created locally with `tools/make_test_clip.py --output .lab/media/synthetic.mp4`.
It contains no operator media or credentials. FFmpeg 7.1 was supplied by the
`imageio-ffmpeg==0.6.0` PyPI wheel in an ignored local tools directory; it is not
an application dependency. Encoding: H.264 Main / yuv420p / 1280x720 / 24 fps,
AAC stereo 48 kHz, 30 seconds, faststart. No encode occurred on Ultra.

The PNG is the independently generated synthetic RGB fixture from
`tools/synthetic_lab.py`; the automated suite checks its chunk CRCs and pixels.

These public assets are suitable only for a public renderer/player probe. They
do not establish application authentication, source delivery or device support.
Generated MSX fixture pages replace every private action with public inline
navigation and public media; their scope notice is deliberate. No proprietary
MSX runtime code is included. Only the official hosted runtime renders/plays them.
