CC=gcc -O2

t_fn : t_fn.c c0n4.c cnm4.c z0nm4.c z1nm4.c zcnm4.c t_fpn4.o t_fpn3.o t_fpn2.o t_fpn1.o
	$(CC) $^ -lquadmath -lm -o $@
t_fpn1.o : t_fpn.c
	$(CC) -c -DNF=1 $^ -o $@
t_fpn2.o : t_fpn.c
	$(CC) -c -DNF=2 $^ -o $@
t_fpn3.o : t_fpn.c
	$(CC) -c -DNF=3 $^ -o $@
t_fpn4.o : t_fpn.c
	$(CC) -c -DNF=4 $^ -o $@

clean :
	rm -vf t_fn t_fpn{1,2,3,4}.o

