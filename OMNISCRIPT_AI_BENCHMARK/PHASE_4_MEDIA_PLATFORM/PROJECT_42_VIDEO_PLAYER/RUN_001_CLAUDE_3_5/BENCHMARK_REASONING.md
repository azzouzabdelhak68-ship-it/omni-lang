# Benchmark Reasoning: Task 4.2 (Video / Video Player)

## Investigation & Decision Log

- **Question**: How should video stream representation and timeline seeking be modeled in OmniScript v6/v7 given that hardware video codecs (`OMNISYS.video`) are not yet natively shipped?
- **Hypothesis**: We can model `MediaInfo` using custom struct types (`type MediaInfo = { source: Text, duration: Number, width: Number, height: Number, bitrate: Number, codec: Text }`), and implement pure metadata extraction, timeline seeking/clamping math, decoding representations, and effectful storage/stream loading (`uses filesystem`).
- **Inspection**: Inspected Project 4.1 (Audio Voice Recorder) and Project 4.3 (Media Capture) which followed similar patterns for audio buffers, synthetic generation, permission lifecycles, and filesystem capability declaration.
- **Probes**: Designed `source/video_player.omni` implementing media model, timeline control (play, pause, seek, current position), metadata extraction, stream loading with `uses filesystem`, and frame decoding.
- **Compiler Checks**: Executed `omni check` and `omni inspect` to verify function signatures, purity, effect declarations (`uses filesystem`), and type soundness.
- **Test Suite**: Implemented `tests/test_video_player.py` using pytest to verify compiler acceptance, metadata model inspection, timeline seek bounds checking (clamping to 0 and duration), and pure/effectful capability checks.
