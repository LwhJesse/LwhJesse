<p align="center">
  <img src="./assets/jesse-banner-light.png#gh-light-mode-only" alt="Jesse signature banner" width="100%" />
  <img src="./assets/jesse-banner-dark.png#gh-dark-mode-only" alt="Jesse signature banner" width="100%" />
</p>

<div align="center">

### GPU Numerical Linear Algebra · Scientific Computing · Open Source Systems

**CUDA · Sparse Solvers · CFD Linear Algebra · Linux Graphics · Arch Linux**

</div>

---

## About

I am an Engineering Mechanics undergraduate working on GPU numerical linear algebra, scientific computing, and open-source systems.

My recent work focuses on CUDA performance engineering, sparse matrix operations, CFD linear algebra infrastructure, and graphics-pipeline debugging, especially where numerical methods meet low-level system behavior.

## Current Focus

- **GPU performance engineering** — CUDA data movement, sparse matrix-vector products, batched GEMM paths, and solver-side performance.
- **Solver correctness and infrastructure** — block-sparse matrix operations, Krylov-solver data flow, and CFD linear algebra paths.
- **Scientific computing** — numerical methods, FEM validation, nonlinear mechanics, and simulation reliability.
- **Linux graphics systems** — Hyprland rendering behavior, ICC/color pipeline issues, blur/transparency debugging, and compositor testing.
- **Open-source contribution workflow** — focused upstream PRs with reproducible benchmarks, minimal patches, and clear validation notes.

## Selected Work

- **SU2 CUDA linear algebra path**  
  Reducing redundant Jacobian uploads during linear solves and investigating CUDA block-sparse matvec correctness in the GPU solver path.

- **CUDA sparse solver optimization**  
  Reusing cuSPARSE SpMV preprocessing in AMGCL's CUDA CSR backend to reduce repeated CSR partition/preprocessing overhead in iterative solves.

- **ArrayFire CUDA batched GEMM**  
  Adding a strided-batched GEMM fast path for compatible batch layouts to avoid pointer-array setup and host-to-device pointer copies.

- **Hyprland ICC / blur rendering investigation**  
  Debugging ICC-enabled blur transparency behavior, compositor work-buffer image descriptions, and color-pipeline interactions on a high-refresh laptop display.

- **Nonlinear beam deflection computation**  
  Numerical calculation and FEM validation for the failure boundary of linear beam theory under large deflection.

- **Arch Linux scientific tooling**  
  Maintaining AUR packages and documentation paths for engineering/scientific software such as OpenSeesPy.

## Technical Stack

<div align="center">

`C++` · `CUDA` · `Python` · `Linux` · `Arch Linux`

`cuSPARSE` · `cuBLAS` · `SpMV` · `Batched GEMM` · `Krylov Solvers` · `Sparse Linear Algebra`

`SU2` · `amgcl` · `ArrayFire` · `CUTLASS` · `OpenSees`

</div>

## GitHub Activity

<div align="center">
  <img src="./profile-summary-card-output/github/0-profile-details.svg#gh-light-mode-only" alt="GitHub profile details" width="80%" />
  <img src="./profile-summary-card-output/github_dark/0-profile-details.svg#gh-dark-mode-only" alt="GitHub profile details" width="80%" />
</div>

<div align="center">
  <img src="./assets/external-contribution-languages-light.svg#gh-light-mode-only" alt="External contribution languages" width="40.5%" />
  <img src="./assets/external-contribution-languages-dark.svg#gh-dark-mode-only" alt="External contribution languages" width="40.5%" />
  <img src="./assets/own-repository-languages-light.svg#gh-light-mode-only" alt="Own repository languages" width="40.5%" />
  <img src="./assets/own-repository-languages-dark.svg#gh-dark-mode-only" alt="Own repository languages" width="40.5%" />
</div>

<br>

<p align="right">
  <img src="./assets/signature-dark.svg#gh-light-mode-only" alt="Jesse signature" width="152" />
  <img src="./assets/signature-light.svg#gh-dark-mode-only" alt="Jesse signature" width="152" />
</p>
