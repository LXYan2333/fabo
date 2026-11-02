"""Checked hooks into QUICK's normal restricted DIIS loop (disposable trees)."""
from pathlib import Path


def patch_training(root, replace_once):
    root = Path(root)
    main = root / 'src/main.f90'
    replace_once(main, '    if (quick_method%SAD) SAFE_CALL(getSadGuess(ierr))',
        '''    block
      character(len=32) :: training_mode
      call get_environment_variable('FABO_SCF_TRAINING', training_mode)
      ! Replay restores the archived SAD state after fullX; no second SAD solve.
      if (trim(training_mode) == 'fixed') quick_method%SAD = .false.
    end block
    if (quick_method%SAD) SAFE_CALL(getSadGuess(ierr))''')
    scf = root / 'src/modules/quick_scf_module.f90'
    replace_once(scf, '\ncontains\n', '''
  logical :: fabo_scf_enabled = .false., fabo_scf_fixed = .false.
  integer :: fabo_scf_count = 0, fabo_scf_steps = 0
  double precision :: fabo_loop_start, fabo_loop_seconds, fabo_fock_start, fabo_iter_start
  double precision, allocatable :: fabo_samples(:,:)
contains
''')
    replace_once(scf, '     done = .false.', '     call fabo_scf_begin()\n     done = .false.')
    replace_once(scf, '\n     jscf=jscf+1\n', '''
     if (fabo_scf_enabled) then
       call fabo_scf_finish()
       stop 0
     endif
     jscf=jscf+1
''')
    replace_once(scf, '     do while (.not.diisdone)', '''     if (fabo_scf_enabled) then
       call fabo_probe_sync()
       call fabo_probe_clock(fabo_loop_start)
     endif
     do while (.not.diisdone)
        if (fabo_scf_enabled) call fabo_probe_clock(fabo_iter_start)''')
    replace_once(scf, '        call scf_operator(deltaO)', '''        if (fabo_scf_enabled) then
          call fabo_probe_sync()
          call fabo_probe_clock(fabo_fock_start)
        endif
        call scf_operator(deltaO)
        if (fabo_scf_enabled) call fabo_scf_fock_end()''')
    old = '           if (PRMS < quick_method%pmaxrms .and. pchange < quick_method%pmaxrms*100.d0 .and. jscf.gt.MIN_SCF)then'
    replace_once(scf, old, old.replace('if (', 'if (.not.fabo_scf_fixed .and. ', 1))
    replace_once(scf, '           if(jscf >= quick_method%iscf-1) then',
                 '           if(.not.fabo_scf_fixed .and. jscf >= quick_method%iscf-1) then')
    replace_once(scf, '           if((tmp .ne. quick_method%integralCutoff).and. .not.diisdone) then', '''           if (fabo_scf_fixed) diisdone = fabo_scf_count >= fabo_scf_steps
           if((tmp .ne. quick_method%integralCutoff).and. .not.diisdone) then''')
    replace_once(scf, '        if (quick_method%debug)  call debug_SCF(jscf)\n     enddo', '''        if (quick_method%debug)  call debug_SCF(jscf)
        if (fabo_scf_enabled) call fabo_scf_iteration_end(PRMS,PCHANGE)
     enddo
     if (fabo_scf_enabled) then
       call fabo_probe_sync()
       call fabo_probe_clock(fabo_loop_seconds)
       fabo_loop_seconds = fabo_loop_seconds - fabo_loop_start
     endif''')
    routines = Path(__file__).with_name('scf_training.f90').read_text()
    replace_once(scf, 'end module quick_scf_module', routines+'\nend module quick_scf_module')
