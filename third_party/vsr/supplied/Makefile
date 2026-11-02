.SUFFIXES:

CC     := nvc
CFLAGS := -Wall -O3 -fast -lm -acc
# CC     := gcc
# CFLAGS := -Wall -O3 -ffast-math -lm -fopenacc

benchmark.x: %.x: %.c \
                  minimax.o \
                  beylkin.o \
                  ishida.o \
                  %.d Makefile
	$(CC) $(wordlist 1,4,$^) -o $@ $(CFLAGS)

benchmark.d: %.d: %.c Makefile
	$(CC) -MM $< -MT $*.x $(CFLAGS) > $@
include benchmark.d

minimax.o: %.o: %.c Makefile
	$(CC) -c $< -o $@ $(CFLAGS)

beylkin.o: %.o: %.c Makefile
	$(CC) -c $< -o $@ $(CFLAGS)

ishida.o: %.o: %.c Makefile
	$(CC) -c $< -o $@ $(CFLAGS)

.PHONY: clean
clean:
	rm -f benchmark.x
	rm -f benchmark.d
	rm -f *.o
