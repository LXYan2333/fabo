"""Checked patches for disposable NWChem 7.3.1 trees, never upstream sources."""
import argparse
from pathlib import Path


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('NWChem source anchor changed: ' + repr(old[:100]))
    return text.replace(old, new)


def patch_simint_cache_helpers(text):
    # NWChem 7.3.1 accidentally guards these energy-path helpers with
    # SIMINT_GRADIENT. Close that inner guard before the common definitions,
    # preserving the outer USE_SIMINT guard and all function bodies.
    text = replace(text, '      integer function nwcsim_cache(bas_in,sh_in)',
                   '#endif\n      integer function nwcsim_cache(bas_in,sh_in)')
    return replace(text, '      end\n#endif\n#else\n      subroutine nwcsim_hf2()',
                   '      end\n#else\n      subroutine nwcsim_hf2()')


def patch(root):
    root = Path(root)
    base = root / 'src/ddscf'
    changes = {}
    path = base / 'rohf.F'
    text = path.read_text()
    text = replace(text, '      logical rohf_diis_solve',
                   '      logical rohf_diis_solve, fabo_nw_diis\n'
                   '      external fabo_nw_diis')
    changes[path] = replace(text, '      else if (odiis) then',
                           '      else if (fabo_nw_diis(odiis)) then')
    path = base / 'rohf_diis.F'
    text = path.read_text()
    text = replace(text, '      logical converged, odo_diis',
                   '      logical converged, odo_diis\n      logical fabo_nw_stop\n      external fabo_nw_stop')
    text = replace(text, '      do iter=1,maxiter',
                   '      call fabo_nw_begin(g_over,g_xorth)\n      do iter=1,maxiter')
    text = replace(text, '        gnorm = sqrt(ga_ddot(g_grad, g_grad))',
                   '        call fabo_nw_evaluated()\n'
                   '        gnorm = sqrt(ga_ddot(g_grad, g_grad))')
    text = replace(text, '        if (converged) goto 333',
                   '        call fabo_nw_record(iter,energy,gnorm)\n'
                   '        if (fabo_nw_stop(iter,converged)) goto 333')
    text = replace(text, ' 333  continue',
                   ' 333  continue\n      call fabo_nw_finish(converged)')
    # Finish uses GA termination after writing diagnostics. The training process
    # intentionally excludes canonicalization and post-SCF properties.
    changes[path] = text + '\n' + Path(__file__).with_name('training_hooks.F').read_text()
    path = base / 'rohf_nr_sol.F'
    text = path.read_text()
    text = replace(text, '      logical converged',
                   '      logical converged, fabo_nw_stop\n'
                   '      external fabo_nw_stop')
    text = replace(text, '\n      time_iter_start = util_wallsec()',
                   '\n      call fabo_nw_begin(0,0)\n'
                   '      time_iter_start = util_wallsec()')
    old = ('            call rohf_step_energy(rtdb, step, g_search,\n'
           '     $           eone, etwo, enrep, ecosmo, energy, g_grad)')
    text = replace(text, old, old+'\n            call fabo_nw_evaluated()')
    # ga_pcg_minim increments iter before returning "accept step". Retain
    # all native line searches/preconditioning; freeze accepted iterations,
    # not energy evaluations, and do not conflate early convergence with stop.
    text = replace(text, '            if ((iter.le.maxiter).and.(.not. converged)) then',
                   '            call fabo_nw_nr_record(\n'
                   '     $           iter-1,energy,gnorm,converged)\n'
                   '            if ((iter.le.maxiter).and.\n'
                   '     $          (.not.fabo_nw_stop(iter-1,converged))) then')
    text = replace(text, '      if (.not.noscf) then  ! bypass for noscf',
                   '      call fabo_nw_finish(converged)\n'
                   '      if (.not.noscf) then  ! bypass for noscf')
    changes[path] = text
    path = base / 'rohf_wrap.F'
    text = path.read_text()
    old = ('      call rohf_fock(rtdb, geom, basis,\n'
           '     $     nclosed, nopen, nmo, tol2e, g_vecs,\n'
           '     $     eone, etwo,\n'
           '     $     crohf_g_fcv, crohf_g_fpv, crohf_g_fcp, oskel, iter )')
    text = replace(text, old, '      call fabo_nw_mark(1,1)\n' + old + '\n      call fabo_nw_mark(1,0)')
    old = ('      call rohf_hessv_xx( basis, geom, nbf, nmo,\n'
           '     $     nclosed, nopen,\n'
           '     $     pflg, g_movecs, oskel, \n'
           '     $     crohf_g_fcv, crohf_g_fpv, crohf_g_fcp,\n'
           '     $     acc, lshift, g_x, g_ax )')
    changes[path] = replace(text, old, '      call fabo_nw_mark(1,1)\n'+old+'\n      call fabo_nw_mark(1,0)')
    path = base / 'rohf_fock.F'
    text = path.read_text()
    old = ('        call fock_2e(geom, basis, nfock, jfactor, kfactor,\n'
           '     $     tol2e, oskel, iv_dens, iv_fock, .false.)')
    changes[path] = replace(text, old, '        call fabo_nw_mark(2,1)\n' + old + '\n        call fabo_nw_mark(2,0)')
    path = base / 'rohf_h2e.F'
    text = path.read_text()
    old = ('      call fock_2e( geom, basis, nfock, jfac, kfac,\n'
           '     $     tol2e, oskel, iv_dens, iv_fock,.false.)')
    changes[path] = replace(text, old, '      call fabo_nw_mark(2,1)\n'+old+'\n      call fabo_nw_mark(2,0)')
    path = base / 'ao_fock_2e.F'
    text = path.read_text()
    # Checked in every measured JK build; a memory-triggered route change must
    # never silently change the training workload.
    changes[path] = replace(text, '      if (oreplicated) then\n         call ao_replicated',
                           '      call fabo_nw_replicated(oreplicated)\n      if (oreplicated) then\n         call ao_replicated')
    path = root/'src/NWints/simint/source/nwcsim_hf2.F'
    changes[path] = patch_simint_cache_helpers(path.read_text())
    # Check all anchors before publishing any modified source.
    for path, text in changes.items():
        path.write_text(text)
    return list(changes)


def patch_single_update(root):
    """One F[P0] and one orbital update, never a convergence trajectory."""
    root=Path(root)
    changed=patch(root)
    path=root/'src/ddscf/rohf_diis.F'
    text=path.read_text()
    text=replace(text, '        call fabo_nw_record(iter,energy,gnorm)\n        if (fabo_nw_stop(iter,converged)) goto 333',
                 'c       Always complete the first diagonalization, even if converged.')
    text=replace(text, '        call ga_copy(g_tmp, g_movecs)',
                 '        call ga_copy(g_tmp, g_movecs)\n'
                 '        call fabo_nw_record(iter,energy,gnorm)\n'
                 '        goto 333')
    text=replace(text, '     $     fabo_nw_diis=requested.and.nmo.eq.nbf',
                 "     $     fabo_nw_diis=requested.and.nmo.eq.nbf\n"
                 "      if (len_trim(mode).ne.0.and.nmo.ne.nbf)\n"
                 "     $ stop 'single-update comparison requires full rank'")
    text=replace(text, '      if (steps.gt.maxiter) stop \'invalid replay bound\'',
                 "      if (steps.ne.1) stop 'comparison requires one update'\n"
                 "      if (steps.gt.maxiter) stop 'invalid replay bound'")
    text=replace(text, '      call ga_terminate()',
                 '      call fabo_nw_dump_matrices()\n'
                 '      call fabo_nw_mkl_report()\n      call ga_terminate()')
    text += '\n'+Path(__file__).with_name('matrices.F').read_text()
    path.write_text(text)
    fock=root/'src/ddscf/rohf_fock.F'
    text=fock.read_text()
    anchor='      call ga_dadd(One, g_hcore, One, g_cfock, g_cfock)'
    text=replace(text,anchor,anchor+'\n      call fabo_nw_capture(g_cdens,g_cfock)')
    fock.write_text(text)
    return changed


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('tree', type=Path)
    patch_single_update(p.parse_args().tree)
