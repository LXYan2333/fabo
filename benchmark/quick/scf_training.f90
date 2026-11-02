! Fixed-length SCF timing hooks; ordinary QUICK DIIS/screening is retained.
  subroutine fabo_scf_begin()
    use allmod
    implicit none
    character(len=1024) :: mode, fixture, steps, legacy
    integer :: unit, ios, magic, n, reduced, electrons
    character :: trailing
    call get_environment_variable('FABO_SCF_TRAINING', mode)
    fabo_scf_enabled = len_trim(mode) > 0
    if (.not.fabo_scf_enabled) return
    if (trim(mode) /= 'calibrate' .and. trim(mode) /= 'fixed') error stop 'invalid SCF training mode'
    call get_environment_variable('FABO_QUICK_MODE', legacy)
    if (len_trim(legacy) /= 0) error stop 'cannot mix fixed-density and SCF probes'
    if (.not.quick_method%HF .or. quick_method%UNRST .or. quick_method%grad .or. quick_method%opt &
        .or. .not.quick_method%diisscf .or. quick_method%divcon .or. quick_method%ecp) &
        error stop 'SCF training requires closed-shell all-electron RHF DIIS'
#ifdef MPIV
    error stop 'SCF training requires a single-process build'
#endif
    fabo_scf_fixed = trim(mode) == 'fixed'
    fabo_scf_count = 0
    fabo_scf_steps = 0
    quick_method%scf_conv = .false.
    call get_environment_variable('FABO_SCF_STATE', fixture)
    if (len_trim(fixture) == 0) error stop 'FABO_SCF_STATE required'
    if (fabo_scf_fixed) then
      call get_environment_variable('FABO_SCF_STEPS', steps)
      read(steps,*,iostat=ios) fabo_scf_steps
      if (ios /= 0) error stop 'invalid fixed iteration count'
      if (fabo_scf_steps < 1 .or. fabo_scf_steps > quick_method%iscf) error stop 'fixed iteration count outside SCF limit'
      open(newunit=unit,file=trim(fixture),access='stream',form='unformatted',status='old')
      read(unit) magic,n,reduced,electrons
      if (magic /= 660801 .or. n /= nbasis .or. reduced /= NBSuse .or. electrons /= quick_molspec%nelec) &
          error stop 'SCF initial-state format/dimensions mismatch'
      call fabo_scf_state_fields(unit,.true.)
      read(unit,iostat=ios) trailing
      if (.not.is_iostat_end(ios)) error stop 'trailing data in SCF initial state'
      close(unit)
      ! The Python worker verifies this replay byte-for-byte before accepting a sample.
      open(newunit=unit,file='replayed-initial.bin',access='stream',form='unformatted',status='new')
    else
      if (.not.quick_method%SAD) error stop 'calibration requires official SAD guess'
      open(newunit=unit,file=trim(fixture),access='stream',form='unformatted',status='new')
    endif
    write(unit) 660801,nbasis,NBSuse,quick_molspec%nelec
    call fabo_scf_state_fields(unit,.false.)
    close(unit)
    allocate(fabo_samples(max(fabo_scf_steps,quick_method%iscf),5))
    fabo_samples = 0.0d0
    call fabo_probe_init()
    call fabo_request_begin()
  end subroutine

  subroutine fabo_scf_state_fields(unit,reading)
    use allmod
    implicit none
    integer, intent(in) :: unit
    logical, intent(in) :: reading
    ! Initial DIIS history is freshly allocated by QUICK. bCalc1e and deltaO
    ! are set by electdiis, which recomputes the first one-electron operator.
    if (reading) then
      read(unit) quick_qm_struct%dense,quick_qm_struct%denseOld,quick_qm_struct%denseSave, &
          quick_qm_struct%co,quick_qm_struct%vec,quick_qm_struct%oldvec,quick_qm_struct%E, &
          quick_qm_struct%s,quick_qm_struct%x,quick_qm_struct%oneElecO,quick_qm_struct%o,quick_qm_struct%oSave, &
          quick_qm_struct%Ecore,quick_qm_struct%Eel
      read(unit) quick_method%integralCutoff,quick_method%primLimit,quick_method%DMCutoff, &
          quick_method%coreIntegralCutoff,quick_method%leastIntegralCutoff,quick_method%maxIntegralCutoff
    else
      write(unit) quick_qm_struct%dense,quick_qm_struct%denseOld,quick_qm_struct%denseSave, &
          quick_qm_struct%co,quick_qm_struct%vec,quick_qm_struct%oldvec,quick_qm_struct%E, &
          quick_qm_struct%s,quick_qm_struct%x,quick_qm_struct%oneElecO,quick_qm_struct%o,quick_qm_struct%oSave, &
          quick_qm_struct%Ecore,quick_qm_struct%Eel
      write(unit) quick_method%integralCutoff,quick_method%primLimit,quick_method%DMCutoff, &
          quick_method%coreIntegralCutoff,quick_method%leastIntegralCutoff,quick_method%maxIntegralCutoff
    endif
  end subroutine

  subroutine fabo_scf_fock_end()
    implicit none
    double precision :: stamp
    call fabo_probe_sync()
    call fabo_probe_clock(stamp)
    fabo_scf_count = fabo_scf_count + 1
    if (fabo_scf_count > size(fabo_samples,1)) error stop 'SCF timing buffer overflow'
    fabo_samples(fabo_scf_count,1) = stamp - fabo_fock_start
  end subroutine

  subroutine fabo_scf_iteration_end(prms,pchange)
    use allmod
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    implicit none
    double precision, intent(in) :: prms,pchange
    double precision :: stamp
    call fabo_probe_sync()
    call fabo_probe_clock(stamp)
    fabo_samples(fabo_scf_count,2:5) = [stamp-fabo_iter_start,quick_qm_struct%Eel+quick_qm_struct%Ecore,prms,pchange]
    if (.not.all(ieee_is_finite(fabo_samples(fabo_scf_count,:)))) error stop 'nonfinite SCF diagnostic'
  end subroutine

  subroutine fabo_scf_finish()
    use allmod
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    implicit none
    integer :: unit,i,j
    call fabo_request_end()
    if (fabo_scf_count < 1) error stop 'SCF loop was not executed'
    if (fabo_scf_fixed .and. fabo_scf_count /= fabo_scf_steps) error stop 'wrong fixed iteration count'
    if (.not.all(ieee_is_finite(quick_qm_struct%dense)) .or. .not.all(ieee_is_finite(quick_qm_struct%o))) &
        error stop 'nonfinite final SCF matrices'
    open(newunit=unit,file='scf-iterations.csv',status='replace')
    write(unit,'(a)') 'iteration,fock_seconds,iteration_seconds,energy_hartree,prms,pchange'
    do i=1,fabo_scf_count
      write(unit,'(i0,5(a,es26.17e3))') i,(',',fabo_samples(i,j),j=1,5)
    enddo
    close(unit)
    open(newunit=unit,file='scf-summary.txt',status='replace')
    write(unit,*) fabo_scf_count,merge(1,0,quick_method%scf_conv),merge(1,0,fabo_scf_fixed)
    write(unit,'(es26.17e3)') fabo_loop_seconds
    write(unit,*) nbasis,NBSuse,quick_molspec%nelec
    close(unit)
    deallocate(fabo_samples)
  end subroutine
