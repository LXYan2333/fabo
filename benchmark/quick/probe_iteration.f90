! Diagnostic fixed-density one-step benchmark, using QUICK routines (MPL-2.0).
  subroutine fabo_probe_iteration(mode)
    use allmod
    use quick_scf_operator_module, only: scf_operator
    use quick_oei_module, only: get1e, bCalc1e
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    implicit none
    character(len=*), intent(in) :: mode
    character(len=1024) :: fixture, warmup_text
    integer :: unit, n, reduced, electrons, rep, warmup, status, k
    double precision :: begin_time, fock_end, end_time, energy
    double precision, allocatable :: p0(:,:), work_rect(:,:), work_sq(:,:), eigvec(:,:), coeff(:,:), eigen(:)

    if (.not.quick_method%HF .or. quick_method%UNRST .or. quick_method%grad .or. quick_method%opt) error stop "probe requires closed-shell RHF energy"
    if (mode /= 'prepare' .and. mode /= 'run' .and. mode /= 'check') error stop "invalid FABO_QUICK_MODE"
    call get_environment_variable('FABO_FIXTURE', fixture)
    if (len_trim(fixture) == 0) error stop "FABO_FIXTURE required"
    call fabo_probe_init()
    allocate(p0(nbasis,nbasis), work_rect(nbasis,NBSuse), work_sq(NBSuse,NBSuse), eigvec(NBSuse,NBSuse), coeff(nbasis,NBSuse), eigen(NBSuse))
    if (mode == 'prepare') then
      quick_qm_struct%o = 0.0d0
      quick_qm_struct%dense = 0.0d0
      call gpu_upload_calculated(quick_qm_struct%o,quick_qm_struct%co,quick_qm_struct%vec,quick_qm_struct%dense)
      bCalc1e = .true.
      call get1e(.false.)
      call MAT_DGEMM('n','n',nbasis,NBSuse,nbasis,1.0d0,quick_qm_struct%oneElecO,nbasis,quick_qm_struct%x,nbasis,0.0d0,work_rect,nbasis)
      call MAT_DGEMM('t','n',NBSuse,NBSuse,nbasis,1.0d0,quick_qm_struct%x,nbasis,work_rect,nbasis,0.0d0,work_sq,NBSuse)
      call MAT_DIAG(work_sq,NBSuse,NBSuse,eigen,eigvec)
      call MAT_DGEMM('n','n',nbasis,NBSuse,NBSuse,1.0d0,quick_qm_struct%x,nbasis,eigvec,NBSuse,0.0d0,coeff,nbasis)
      call MAT_DGEMM('n','t',nbasis,nbasis,quick_molspec%nelec/2,2.0d0,coeff,nbasis,coeff,nbasis,0.0d0,p0,nbasis)
      call fabo_probe_sync()
      if (.not.all(ieee_is_finite(p0))) error stop "nonfinite P0"
      open(newunit=unit,file=trim(fixture),access='stream',form='unformatted',status='new')
      write(unit) nbasis,NBSuse,quick_molspec%nelec
      write(unit) p0,quick_qm_struct%oneElecO,quick_qm_struct%s,quick_qm_struct%x
      close(unit)
      open(newunit=unit,file='fixture-info.txt',status='replace')
      write(unit,*) nbasis,NBSuse,quick_molspec%nelec,quick_qm_struct%Ecore
      close(unit)
      return
    endif

    open(newunit=unit,file=trim(fixture),access='stream',form='unformatted',status='old')
    read(unit) n,reduced,electrons
    if (n /= nbasis .or. reduced /= NBSuse .or. electrons /= quick_molspec%nelec) error stop "fixture dimensions mismatch"
    read(unit) p0,quick_qm_struct%oneElecO,quick_qm_struct%s,quick_qm_struct%x
    close(unit)
    bCalc1e = .false.
    warmup = 1
    call get_environment_variable('FABO_WARMUP',warmup_text,status=status)
    if (status == 0 .and. len_trim(warmup_text) > 0) read(warmup_text,*) warmup
    if (warmup < 0) error stop "negative warmup"
    if (mode == 'check') warmup = 0
    if (mode /= 'check') then
    open(newunit=unit,file='timings.csv',status='replace')
    write(unit,'(a)') 'iteration,fock_seconds,iteration_seconds,energy_diagnostic'
    endif
    do rep=0,warmup
      quick_qm_struct%dense = p0
      quick_qm_struct%denseOld = p0
      quick_qm_struct%o = 0.0d0
      quick_qm_struct%co = 0.0d0
      quick_qm_struct%vec = 0.0d0
      call fabo_probe_sync()
      if (mode /= 'check') call fabo_probe_clock(begin_time)
      call scf_operator(.false.)
      call fabo_probe_sync()
      if (mode /= 'check') call fabo_probe_clock(fock_end)
      call MAT_DGEMM('n','n',nbasis,NBSuse,nbasis,1.0d0,quick_qm_struct%o,nbasis,quick_qm_struct%x,nbasis,0.0d0,work_rect,nbasis)
      call MAT_DGEMM('t','n',NBSuse,NBSuse,nbasis,1.0d0,quick_qm_struct%x,nbasis,work_rect,nbasis,0.0d0,work_sq,NBSuse)
      call MAT_DIAG(work_sq,NBSuse,NBSuse,eigen,eigvec)
      call MAT_DGEMM('n','n',nbasis,NBSuse,NBSuse,1.0d0,quick_qm_struct%x,nbasis,eigvec,NBSuse,0.0d0,coeff,nbasis)
      call MAT_DGEMM('n','t',nbasis,nbasis,quick_molspec%nelec/2,2.0d0,coeff,nbasis,coeff,nbasis,0.0d0,quick_qm_struct%dense,nbasis)
      call fabo_probe_sync()
      if (mode /= 'check') call fabo_probe_clock(end_time)
      if (.not.all(ieee_is_finite(quick_qm_struct%o)) .or. .not.all(ieee_is_finite(quick_qm_struct%dense))) error stop "nonfinite output"
      energy = quick_qm_struct%Ecore + 0.5d0*sum(p0*(quick_qm_struct%oneElecO+quick_qm_struct%o))
      if (mode /= 'check' .and. rep == warmup) write(unit,'(i0,3(a,es24.16e3))') 1,',',fock_end-begin_time,',',end_time-begin_time,',',energy
    enddo
    if (mode /= 'check') close(unit)
    if (mode == 'check') then
      open(newunit=unit,file='check-energy.txt',status='replace')
      write(unit,'(es26.17e3)') energy
      close(unit)
    endif
    open(newunit=unit,file='outputs.bin',access='stream',form='unformatted',status='replace')
    write(unit) quick_qm_struct%o,quick_qm_struct%dense
    close(unit)
    call fabo_probe_counts()
    deallocate(p0,work_rect,work_sq,eigvec,coeff,eigen)
  end subroutine fabo_probe_iteration
