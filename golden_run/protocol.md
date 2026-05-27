# Golden Run Protocol: Autonomous Optimization Loop
# Target: Match or exceed 11 triggers in < 105s

## Loop Protocol
1. **Benchmark:** Run `python main.py --test-file tests/test_audio.wav`.
2. **Analyze:** Check if triggers == 11 and total_time <= 105s.
3. **Optimize:** 
    - If triggered < 11: Adjust `vector_threshold` in `config.ini`.
    - If time > 105s: Optimize transcription parameters in `transcriber.py`.
4. **Log:** Append results to `reply.md` with [RESPONSE #N].
5. **Repeat:** Loop until condition met.

## Current Target Metrics
- Verses: 11
- Runtime: 105s
- Latency: < 5s per trigger
