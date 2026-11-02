module allmod
  implicit none
  integer :: nbasis=2, NBSuse=2
  type method
    logical :: HF=.true., UNRST=.false., grad=.false., opt=.false., diisscf=.true.
    logical :: divcon=.false., ecp=.false., SAD=.true., scf_conv=.false.
    integer :: iscf=10
    double precision :: integralCutoff=1d-8, primLimit=1d-9, DMCutoff=1d-8
    double precision :: coreIntegralCutoff=1d-12, leastIntegralCutoff=1d-6, maxIntegralCutoff=1d-12
  end type
  type molecule
    integer :: nelec=2
  end type
  type state
    double precision :: dense(2,2)=1, denseOld(2,2)=2, denseSave(2,2)=3
    double precision :: co(2,2)=4, vec(2,2)=5, oldvec(2,2)=6, E(2)=7
    double precision :: s(2,2)=8, x(2,2)=9, oneElecO(2,2)=10, o(2,2)=11, oSave(2,2)=12
    double precision :: Ecore=13, Eel=14
  end type
  type(method) :: quick_method
  type(molecule) :: quick_molspec
  type(state) :: quick_qm_struct
end module

module hooks
  logical :: fabo_scf_enabled=.false., fabo_scf_fixed=.false.
  integer :: fabo_scf_count=0, fabo_scf_steps=0
  double precision :: fabo_loop_start, fabo_loop_seconds, fabo_fock_start, fabo_iter_start
  double precision, allocatable :: fabo_samples(:,:)
contains
! INSERT_PRODUCTION_ROUTINES
end module

subroutine fabo_request_begin()
end subroutine
subroutine fabo_request_end()
end subroutine
subroutine fabo_probe_init()
end subroutine
subroutine fabo_probe_sync()
end subroutine
subroutine fabo_probe_clock(t)
  double precision :: t
  double precision, save :: clock=0
  clock=clock+0.01d0
  t=clock
end subroutine

program test
  use allmod
  use hooks
  integer :: i,n
  character(len=32) :: mode
  call get_environment_variable('FABO_SCF_TRAINING',mode)
  if (trim(mode)=='fixed') quick_qm_struct%dense=-999
  call fabo_scf_begin()
  if (.not.all(quick_qm_struct%dense==1)) error stop 'state not restored'
  n=2
  if (fabo_scf_fixed) n=fabo_scf_steps
  call fabo_probe_clock(fabo_loop_start)
  do i=1,n
    call fabo_probe_clock(fabo_iter_start)
    call fabo_probe_clock(fabo_fock_start)
    call fabo_scf_fock_end()
    call fabo_scf_iteration_end(0.1d0,0.1d0)
  enddo
  call fabo_probe_clock(fabo_loop_seconds)
  fabo_loop_seconds=fabo_loop_seconds-fabo_loop_start
  call fabo_scf_finish()
end program
