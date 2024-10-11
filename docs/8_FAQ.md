# Frequently asked questions

### Processing one ORC takes a long time, is it normal ?

Yes ! Parsing a large amount of data takes time.

Processing an Offline ORC of 1,7G on a laptop with i5 CPU (1.60GHz) with a single thread takes 12 minutes. When using 4 threads on the same laptop, it takes less that 8 minutes.

Processing an ORC of 500M can take 20 minutes when using 4 threads.

### Why does doubling the number of threads not halve the time of processing by two ?

The processing can be divided in two parts. The first part is plugin execution, it ends only when the last plugin instance reaches its end. Only after that, orc2timeline begins to merge plugin timelines into final timelines.

If a plugin instance takes significantly longer, it will have an impact on orc2timeline execution time.

Nevertheless it is worth mentioning that the more ORC are processed in parallel, the more effective orc2timeline will be.

Do not hesitate to run orc2timeline against a directory with a large number of ORC in it.

### My laptop freezes while running orc2timeline ?

orc2timeline can slow down your laptop. There can be two reasons that may explain this behavior. First orc2timeline may cause RAM exhaustion, second orc2timeline may use too much CPU.

You can choose to use less threads, orc2timeline should then use less CPU and memory.

Concerning memory consumption, another adjustment may be useful: you could decrease the size of chunks (line 198 of file GenericToTimeline.py), orc2timeline will use less memory, but will be less effective.

### My disk is out of space ?

orc2timeline writes a lot of things on the disk, it may require a large amount of space. `TMP_DIR` global variable can be used to specify a directory to write temporary files to. The option `--tmp-directory` has the same effect.
