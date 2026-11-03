c     Common capture handles; copies are included in complete-update timing,
c     but not the nested JK timer. All serialization is after timing stops.
      subroutine fabo_nw_capture(density,fock,hcore)
      implicit none
#include "global.fh"
      integer density,fock,hcore,saved_h,saved_d,saved_f,captures
      common /fabo_nw_matrices/ saved_d,saved_f,saved_h,captures
      captures=captures+1
      if (captures.ne.1) stop 'more than one Fock evaluation'
      if (.not.ga_duplicate(density,saved_d,'saved P0')) stop
      if (.not.ga_duplicate(fock,saved_f,'saved F')) stop
      call ga_copy(density,saved_d)
      call ga_copy(fock,saved_f)
      if (.not.ga_duplicate(hcore,saved_h,'saved H')) stop
      call ga_copy(hcore,saved_h)
      end

      subroutine fabo_nw_dump_energy(energy)
      implicit none
      double precision energy
      integer unit
      open(newunit=unit,file='energy.bin',status='new',
     $ access='stream',form='unformatted')
      write(unit) energy
      close(unit)
      end

      block data fabo_nw_matrices_init
      integer saved_d,saved_f,saved_h,captures
      common /fabo_nw_matrices/ saved_d,saved_f,saved_h,captures
      data saved_d,saved_f,saved_h,captures/0,0,0,0/
      end

      subroutine fabo_nw_dump_matrices()
      implicit none
#include "global.fh"
#include "cscf.fh"
#include "mafdecls.fh"
      integer saved_d,saved_f,saved_h,captures,p1,unused
      common /fabo_nw_matrices/ saved_d,saved_f,saved_h,captures
      if (captures.ne.1) stop 'wrong Fock count'
      call fabo_nw_dump('density-in.bin',saved_d)
      call fabo_nw_dump('fock.bin',saved_f)
      call fabo_nw_dump('hcore.bin',saved_h)
      if (.not.ga_duplicate(saved_d,p1,'P1')) stop
      unused=0
      call rohf_dens(g_movecs(1),nbf,nclosed,nopen,p1,unused)
      call fabo_nw_dump('density-out.bin',p1)
      if (.not.ga_destroy(p1)) stop
      if (.not.ga_destroy(saved_d)) stop
      if (.not.ga_destroy(saved_f)) stop
      if (.not.ga_destroy(saved_h)) stop
      end

      subroutine fabo_nw_dump(filename,handle)
      use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
      implicit none
#include "global.fh"
      character*(*) filename
      integer handle,itype,n,m,unit
      double precision, allocatable :: buf(:,:)
      call ga_inquire(handle,itype,n,m)
      allocate(buf(n,m))
      call ga_get(handle,1,n,1,m,buf,n)
      if (.not.all(ieee_is_finite(buf))) stop 'nonfinite matrix'
      open(newunit=unit,file=filename,status='new',
     $ access='stream',form='unformatted')
c     Headerless column-major binary64; dimensions are in scf-protocol.txt.
      write(unit) buf
      close(unit)
      deallocate(buf)
      end
