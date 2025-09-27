# Trusted Capture & Proof Architecture

This document outlines how we can prove that each orchestrator is running a unique, genuine Unreal Engine stream and serving the exact assets/scripts we issued. The flow combines hardware-backed attestation, deterministic hashing, and zero-knowledge proofs.

## 1. Trust Tiers

| Tier | Requirements | Guarantees | Payout Policy |
|------|--------------|------------|---------------|
| A – Trusted Capture | Host exposes a TEE (Nitro Enclave / SEV-SNP / TDX) + GPU telemetry. | Attested Unreal build, unique GPU UUID, tamper-proof frame hashes. | Automatic payouts once proofs & hashes check out. |
| B – Untrusted Capture | Host lacks TEE support. | Only zk proof + hashes provided by operator, no hardware guarantee. | Manual review, reduced payout, or bond requirement. |

Registrations record `capture_trust_level = trusted|untrusted`. The processor enforces different payout paths per tier.

## 2. Runtime Flow (Tier A)

1. **Nonce issue** – Payments backend issues a fresh nonce whenever the orchestrator authenticates or rotates its session (even if no script is queued yet).
2. **Unreal launch** – Orchestrator runs our signed UE build plus the embedded telemetry module, which is always active while the instance is online.
3. **TEE capture agent** – A helper process runs inside the enclave/confidential VM and, on a fixed schedule (e.g., every minute):
   - Reads Unreal telemetry via shared memory / REST within the host.
   - Grabs frame samples from the GPU (CUDA interop or NVFBC) even if the avatar is idle or only default animation is playing.
   - Computes cryptographic hashes (BLAKE3/SHA-256) of that sampling window.
   - Collects script execution logs (command timestamps, audio asset IDs) if any commands fired during the period; otherwise it records an empty-but-signed interval to prove continuous operation.
4. **Attestation** – After each sampling window, the enclave produces a quote containing:
   - Hash of the Unreal build package.
   - Backend nonce.
   - GPU UUID + driver info.
   - Merkle root of frame hashes over the sampling window (present even when only default output is shown).
   - Merkle root of command log entries (empty root if no scripted actions).
5. **Proof submission** – Every interval (e.g., once per minute) the orchestrator sends to `/api/orchestrators/submit-proof`:
   - Attestation quote (TEE signed data).
   - zk proof that the script + asset hashes for that interval match the backend commitments (or that no scripted actions occurred).
   - The raw frame hashes and command log for audit.

## 3. zk Proof Scope

We leverage a zkVM (Risc0/Boojum) to prove:

- The command sequence executed matches the committed script_root. Each step is hashed as `H(type || payload || delay_ms)`.
- Every audio/video asset invoked matches the committed asset Merkle root.
- Optional: Timing bounds (e.g., delays were at least the specified minimum).
- Public inputs: script_root, asset_root, backend nonce, frame_hash_root.
- Private inputs: ordered steps, asset IDs, raw frame hashes (or chunk hashes).

The zk proof binds the captured telemetry to the commitments. The enclave attestation ensures the telemetry is authentic.

## 4. Backend Verification

The payments backend maintains per-orchestrator records:

```json
{
  "capture_trust_level": "trusted",
  "tee_quote": { ... },
  "gpu_uuid": "GPU-1234",
  "last_nonce": "0xabc",
  "script_root": "...",
  "asset_root": "...",
  "frame_root": "...",
  "last_proof_at": "2025-09-26T21:04:00Z",
  "proof_hash": "..."
}
```

Verification steps:

1. Validate the TEE quote using the vendor’s SDK; ensure the measurement matches our expected enclave image + UE build hash, and the nonce matches `last_nonce`.
2. Verify the zk proof (public inputs match registry values).
3. Ensure `gpu_uuid` is not claimed by another orchestrator and has not re-attested with a different nonce without finishing the previous session.
4. Check frame hash root against the attested value.
5. Mark cycle as verified; store proof hash + attested frame hash window.

Payout loop credits only when `capture_trust_level = trusted` **and** the most recent proof & attestation are fresh (within X minutes). Otherwise, orchestrator remains in “paused” state.

## 5. Frame Hashing Strategy

- Sample once per second (configurable) regardless of activity level. Each sample: read framebuffer (or NVENC output) and hash via BLAKE3.
- Aggregate 60 samples into a Merkle tree per minute; store the root in the attestation even if the frames all match the idle avatar feed.
- Retain raw hashes for audit; backend can recompute if needed.
- If bandwidth is a concern, allow downsampled images (quarter resolution) but document the quality impact.

## 6. Tier B Handling

For orchestrators without TEE support:

- Still compute frame hashes & zk proof, but mark attestation as `capture_trust_level = untrusted`.
- Require manual approval or reduced payout multiplier.
- Encourage upgrade path by documenting supported instance types and providing scripts to provision TEE hosts.

## 7. Failure & Rotation

- Nonce timeouts: if attestation/proof not received within N minutes, invalidate the nonce and stop crediting.
- Enclave restart: require new attestation; backend updates `last_nonce`.
- Proof failure: trigger cooldown and manual investigation.
- Audit logs: attic store all proofs, frame roots, and quotes for compliance.

## 8. Next Steps

1. Build Unreal telemetry module and enclave agent prototype (staging). 
2. Integrate zkVM proof generator in orchestrator runner. 
3. Add `/api/orchestrators/submit-proof` and update registry schema. 
4. Modify payment processor to enforce fresh proof + attestation. 
5. Update docs for Tier A/B operators.
