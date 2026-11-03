c     Training-only hooks. Included in the disposable rohf_diis.F object.
c     Full-rank DIIS or native reduced-rank NR/PCG, with normal screening.
      block data fabo_nw_initial
      implicit none
      logical active,fixed
      integer steps,count
      integer solver,evals,eval_samples(10000)
      common /fabo_nw_protocol/ solver,evals,eval_samples
      double precision starts(3),totals(2),samples(10000,5)
      common /fabo_nw_state/ active,fixed,steps,count,
     $     starts,totals,samples
      data active,fixed/.false.,.false./
      data steps,count/0,0/
      data solver,evals/0,0/
      end

      logical function fabo_nw_diis(requested)
      implicit none
#include "cscf.fh"
      logical requested
      character*32 mode
      call get_environment_variable('FABO_NWCHEM_MODE',mode)
      fabo_nw_diis=requested
c     The pinned DIIS routine requires square MO arrays. Native NR/PCG
c     supports the reduced space selected by ordinary overlap filtering.
      if (len_trim(mode).ne.0)
     $     fabo_nw_diis=requested.and.nmo.eq.nbf
      end

      subroutine fabo_nw_begin(g_over,g_xorth)
      implicit none
#include "global.fh"
#include "cscf.fh"
#include "mafdecls.fh"
#include "util.fh"
      integer g_over,g_xorth,unit,ios,magic,dims(5),i
      integer solver,evals,eval_samples(10000)
      common /fabo_nw_protocol/ solver,evals,eval_samples
      character*32 mode,step_text
      character*1 trailing
      logical active,fixed,reading
      integer steps,count
      double precision starts(3),totals(2),samples(10000,5)
      common /fabo_nw_state/ active,fixed,steps,count,
     $     starts,totals,samples
      call get_environment_variable('FABO_NWCHEM_MODE',mode)
      if (len_trim(mode).eq.0) return
      if (mode.ne.'calibrate'.and.mode.ne.'calibrate_cap'.and.
     $    mode.ne.'replay')
     $     stop 'invalid FABO_NWCHEM_MODE'
      if (ga_nnodes().ne.1.or.nopen.ne.0)
     $     stop 'training requires one rank and closed-shell RHF'
      if (nmo.lt.1.or.nmo.gt.nbf.or.nclosed.gt.nmo)
     $     stop 'invalid training orbital dimensions'
      solver=1
      if (g_over.eq.0.and.g_xorth.eq.0) solver=2
      if (solver.eq.1.and.nmo.ne.nbf)
     $     stop 'DIIS training requires full-rank orbitals'
      evals=0
      if (maxiter.gt.10000) stop 'training iteration limit exceeded'
      fixed=mode.eq.'replay'
      steps=0
      if (mode.eq.'calibrate_cap') steps=maxiter
      count=0
      totals=0d0
      if (fixed) then
         call get_environment_variable('FABO_NWCHEM_STEPS',step_text)
         read(step_text,*,iostat=ios) steps
         if (ios.ne.0) stop 'invalid replay iteration count'
         if (steps.lt.1.or.steps.gt.10000) stop 'invalid replay bound'
c        Native NR can extend maxiter when changing its preconditioner.
c        Replay starts from the input limit but must admit the calibrated
c        accepted-step count, including any such native extension.
         if (solver.eq.2) maxiter=max(maxiter,steps)
         if (steps.gt.maxiter) stop 'invalid replay bound'
         open(newunit=unit,file='initial.bin',status='old',
     $        access='stream',form='unformatted')
         read(unit) magic,dims
         if (magic.ne.660803.or.dims(1).ne.nbf.or.
     $       dims(2).ne.nmo.or.dims(3).ne.nclosed.or.
     $       dims(4).ne.nopen.or.dims(5).ne.solver)
     $       stop 'initial state mismatch'
         read(unit) dbl_mb(k_occ:k_occ+nmo-1),
     $              dbl_mb(k_eval:k_eval+nmo-1)
         reading=.true.
         call fabo_nw_array(unit,reading,g_movecs(1),nbf,nmo)
         if (solver.eq.1) then
            call fabo_nw_array(unit,reading,g_over,nbf,nbf)
            call fabo_nw_array(unit,reading,g_xorth,nbf,nbf)
         endif
         read(unit,iostat=ios) trailing
         if (ios.ge.0) stop 'initial state has trailing data'
         close(unit)
         open(newunit=unit,file='replayed.bin',status='new',
     $        access='stream',form='unformatted')
      else
         open(newunit=unit,file='initial.bin',status='new',
     $        access='stream',form='unformatted')
      endif
      write(unit) 660803,nbf,nmo,nclosed,nopen,solver
      write(unit) dbl_mb(k_occ:k_occ+nmo-1),
     $            dbl_mb(k_eval:k_eval+nmo-1)
      reading=.false.
      call fabo_nw_array(unit,reading,g_movecs(1),nbf,nmo)
      if (solver.eq.1) then
         call fabo_nw_array(unit,reading,g_over,nbf,nbf)
         call fabo_nw_array(unit,reading,g_xorth,nbf,nbf)
      endif
      close(unit)
      active=.true.
      call fabo_request_begin()
      starts(3)=util_wallsec()
      end

      subroutine fabo_nw_array(unit,reading,handle,n,m)
      use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
      implicit none
#include "global.fh"
      integer unit,handle,n,m,itype,rows,cols
      logical reading
      double precision, allocatable :: buf(:,:)
      call ga_inquire(handle,itype,rows,cols)
      if (rows.ne.n.or.cols.ne.m) stop 'training GA shape mismatch'
      allocate(buf(n,m))
      if (reading) then
         read(unit) buf
         if (.not.all(ieee_is_finite(buf))) stop 'nonfinite state'
         call ga_put(handle,1,n,1,m,buf,n)
      else
         call ga_get(handle,1,n,1,m,buf,n)
         if (.not.all(ieee_is_finite(buf))) stop 'nonfinite state'
         write(unit) buf
      endif
      deallocate(buf)
      end

      subroutine fabo_nw_evaluated()
      implicit none
      integer solver,evals,eval_samples(10000)
      common /fabo_nw_protocol/ solver,evals,eval_samples
      evals=evals+1
      end

      subroutine fabo_nw_nr_record(iteration,energy,gnorm,converged)
      implicit none
      integer iteration,steps,count
      logical converged,active,fixed
      double precision energy,gnorm
      double precision starts(3),totals(2),samples(10000,5)
      common /fabo_nw_state/ active,fixed,steps,count,
     $     starts,totals,samples
      call fabo_nw_record(iteration,energy,gnorm)
c     The native reverse-communication loop also tests converged at its
c     entry. Suppress early termination only while fixed replay continues.
      if (active.and.fixed.and.count.lt.steps) converged=.false.
      end

      subroutine fabo_nw_mark(scope,beginning)
      implicit none
#include "util.fh"
      integer scope,beginning
      logical active,fixed
      integer steps,count
      double precision starts(3),totals(2),samples(10000,5)
      common /fabo_nw_state/ active,fixed,steps,count,
     $     starts,totals,samples
      if (.not.active) return
      if (beginning.eq.1) then
         starts(scope)=util_wallsec()
      else
         totals(scope)=totals(scope)+util_wallsec()-starts(scope)
      endif
      end

      subroutine fabo_nw_record(iteration,energy,gnorm)
      implicit none
#include "util.fh"
      integer iteration
      double precision energy,gnorm
      logical active,fixed
      integer steps,count
      integer solver,evals,eval_samples(10000)
      common /fabo_nw_protocol/ solver,evals,eval_samples
      double precision starts(3),totals(2),samples(10000,5)
      common /fabo_nw_state/ active,fixed,steps,count,
     $     starts,totals,samples
      if (.not.active) return
      count=count+1
      if (count.ne.iteration.or.count.gt.10000)
     $     stop 'unexpected solver iteration count'
      samples(count,1:2)=totals
      samples(count,3)=util_wallsec()-starts(3)
      samples(count,4)=energy
      samples(count,5)=gnorm
      eval_samples(count)=evals
      end

      logical function fabo_nw_stop(iteration,converged)
      implicit none
      integer iteration
      logical converged,active,fixed
      integer steps,count
      double precision starts(3),totals(2),samples(10000,5)
      common /fabo_nw_state/ active,fixed,steps,count,
     $     starts,totals,samples
      fabo_nw_stop=converged
      if (active.and..not.fixed.and.steps.gt.0)
     $     fabo_nw_stop=converged.or.iteration.ge.steps
      if (active.and.fixed) fabo_nw_stop=iteration.ge.steps
      end

      subroutine fabo_nw_replicated(replicated)
      implicit none
      logical replicated,active,fixed
      integer steps,count
      double precision starts(3),totals(2),samples(10000,5)
      common /fabo_nw_state/ active,fixed,steps,count,
     $     starts,totals,samples
      if (active.and..not.replicated)
     $     stop 'replicated Fock route changed: increase memory'
      end

      subroutine fabo_nw_finish(converged)
      use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
      implicit none
#include "global.fh"
#include "util.fh"
#include "cscf.fh"
      logical converged,active,fixed
      integer steps,count,unit,i,j
      integer solver,evals,eval_samples(10000)
      common /fabo_nw_protocol/ solver,evals,eval_samples
      double precision starts(3),totals(2),samples(10000,5),elapsed
      common /fabo_nw_state/ active,fixed,steps,count,
     $     starts,totals,samples
      if (.not.active) return
      elapsed=util_wallsec()-starts(3)
      active=.false.
      call fabo_request_end()
      if (count.lt.1) stop 'no SCF iterations'
      if (fixed.and.count.ne.steps) stop 'wrong replay length'
      if (.not.all(ieee_is_finite(samples(1:count,:))))
     $     stop 'nonfinite SCF diagnostic'
      open(newunit=unit,file='scf-iterations.csv',status='new')
      write(unit,'(a)') 'iteration,fock_seconds,jk_seconds,'//
     $     'scf_seconds,energy_hartree,gradient_norm,'//
     $     'energy_gradient_evaluations'
      do i=1,count
         write(unit,'(i0,5(a,es26.17e3),a,i0)')
     $        i,(',',samples(i,j),j=1,5),',',eval_samples(i)
      enddo
      close(unit)
      open(newunit=unit,file='scf-summary.txt',status='new')
      write(unit,*) count,merge(1,0,converged),merge(1,0,fixed)
      write(unit,'(es26.17e3)') elapsed
      close(unit)
c     Solver and dimensions are frozen in initial.bin and the replay echo.
      open(newunit=unit,file='scf-protocol.txt',status='new')
      write(unit,*) solver,nbf,nmo,evals
      close(unit)
c     No canonicalization or post-SCF property work in a training process.
      call ga_terminate()
      call mpi_finalize(i)
      stop
      end
