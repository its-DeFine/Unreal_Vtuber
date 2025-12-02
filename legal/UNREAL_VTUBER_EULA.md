# Unreal VTuber Pixel Streaming Stack – License and Use Terms

_Last updated: 2025‑12‑02_

These terms govern your use of the proprietary Unreal VTuber Pixel Streaming
stack authored and operated by **Atumera Inc.** (“**Atumera**”, “**we**”, “**us**”).
By building, pulling, running, or otherwise using the container images and
scripts described in this repository, you agree to be bound by these terms.

If you do not agree, you must not use the software.

---

## 1. Scope and definitions

For purposes of these terms:

- “**Stack**” means the Unreal VTuber Pixel Streaming orchestration described in
  this repository, including without limitation the container images:
  - `ghcr.io/its-define/unreal_vtuber/embody-ue-ps` (game container),
  - `ghcr.io/its-define/unreal_vtuber/embody-signaling`,
  - `ghcr.io/its-define/unreal_vtuber/embody-turn-server`,
  - any Atumera-provided script‑runner, recorder, watchdog, auto‑updater, or
    health‑monitor containers; and
  - the associated orchestration scripts and configuration shipped here.

- “**Software**” means the Stack together with all associated code, assets,
  configuration, and documentation that Atumera provides for operating an
  Unreal VTuber orchestrator node.

- “**You**” means the individual or legal entity that accesses or uses the
  Software. If you use the Software on behalf of an organization, you represent
  that you are authorized to bind that organization to these terms.

Third‑party components (including Epic Games’ Unreal Engine, Pixel Streaming
tooling, and other open‑source dependencies) are licensed under their own
terms. Those third‑party licenses govern your rights in those components and
are not modified by this EULA.

---

## 2. License grant

Subject to your ongoing compliance with these terms, Atumera grants you a
limited, revocable, non‑exclusive, non‑transferable, non‑sublicensable license
to:

- pull and run the Software on infrastructure you control, and
- use the Software solely to operate a pixel‑streamed Unreal VTuber instance
  as an orchestrator or test node that Atumera (or its designated programs)
  has expressly authorized.

No rights are granted to use the Software for any other purpose.

---

## 3. Ownership

The Software is licensed, not sold. As between you and Atumera:

- Atumera owns all right, title, and interest in and to the Software, including
  all code, container images, configuration, and documentation it provides,
  together with all associated trademarks, trade dress, and other intellectual
  property.
- You own your own data, content, and infrastructure.

Except for the limited license expressly granted in Section 2, Atumera reserves
all rights in and to the Software. No implied licenses are granted.

---

## 4. Restrictions (no reverse engineering / no copycats)

You must not, and must not permit any third party to:

1. **Reverse engineer or decompile** any part of the Software, including the
   game container and Pixel Streaming containers, or attempt to derive their
   source code, underlying models, or design except to the limited extent
   allowed by applicable law notwithstanding this restriction.
2. **Modify, adapt, or create derivative works** of the Software, including
   repackaging or re‑branding the containers for third‑party use, white‑label
   offerings, or competing products.
3. **Redistribute, resell, or sublicense** the Software, the container images,
   or any access credentials (tokens, keys, or registry accounts) provided by
   Atumera, whether for a fee or free, to any third party.
4. **Host for third parties** as a general‑purpose service, SaaS, or platform
   unless you have a separate written agreement with Atumera explicitly
   permitting this.
5. **Bypass or interfere with access controls**, license checks, API tokens,
   or security mechanisms designed to restrict how the Software is used or who
   can access it.
6. **Extract or reuse assets** (models, textures, blueprints, UI assets, or
   other content) from the game or pixel‑streaming containers for use outside
   the orchestrator context authorized by Atumera.
7. **Use the Software to train or evaluate models** (including but not limited
   to LLMs, diffusion models, or other AI systems) in a way that competes with
   or replicates Atumera’s products or services, unless expressly permitted in
   writing.
8. **Remove, obscure, or alter notices** (copyright, trademark, or attribution)
   contained in the Software.

Any use outside the orchestrator use‑case authorized by Atumera—including
copying the game or pixel‑streaming containers for unrelated projects or
products—is strictly prohibited.

---

## 5. Third‑party technology

The Software may bundle or integrate:

- Epic Games’ Unreal Engine and Pixel Streaming components,
- other third‑party libraries, tools, and frontends, and
- open‑source dependencies under their own licenses.

Those third‑party components are subject to their own license terms. Nothing in
this EULA limits your rights under those licenses, but you receive **no**
additional rights from Atumera beyond what those licenses already grant.

Where this EULA conflicts with a third‑party license for a particular
component, the third‑party license governs your use of that component; this
EULA governs the Atumera‑authored portions and the Stack as a whole.

---

## 6. Access credentials and registry use

If Atumera provides you with access credentials (for example: GitHub, GHCR, or
TURN/STUN credentials) for pulling and running the Software:

- you must treat those credentials as confidential,
- you must use them only for the orchestrators and environments Atumera has
  authorized, and
- you must not share those credentials with third parties or embed them in
  public code, images, or repositories.

Atumera may revoke or rotate credentials at any time to prevent misuse.

---

## 7. Updates and auto‑updates

The Stack may include auto‑update components (such as watchtower) that pull
new images tagged for orchestrator use. By deploying the Stack, you authorize
these update mechanisms to:

- query the registries configured in your environment, and
- pull and run new builds of the containers they manage.

You remain responsible for pinning tags, disabling auto‑updates, or adjusting
the configuration if you need stricter change control in your environment.

---

## 8. Term and termination

This license remains in effect until terminated.

Atumera may suspend or terminate your license immediately if you:

- breach these terms, or
- use the Software in a way that Atumera reasonably believes harms its
  infrastructure, IP, or partners.

Upon termination:

- you must stop all use of the Software,
- you must delete all copies of Atumera‑provided container images, scripts, and
  configuration from your systems, and
- Sections 3–10 survive.

---

## 9. No warranties

THE SOFTWARE IS PROVIDED “AS IS” AND “AS AVAILABLE”, WITH ALL FAULTS AND
WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, OR STATUTORY,
INCLUDING WITHOUT LIMITATION ANY IMPLIED WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON‑INFRINGEMENT.

You are solely responsible for securing and operating your own infrastructure,
for validating updates before roll‑out, and for any content or data you
process with the Stack.

---

## 10. Limitation of liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW, ATUMERA AND ITS AFFILIATES WILL NOT BE
LIABLE FOR:

- INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR
- ANY LOSS OF PROFITS, REVENUE, DATA, OR GOODWILL,

ARISING OUT OF OR RELATING TO THE SOFTWARE OR THESE TERMS, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGES.

ATUMERA’S AGGREGATE LIABILITY FOR ALL CLAIMS RELATING TO THE SOFTWARE WILL NOT
EXCEED THE GREATER OF (A) THE AMOUNTS YOU PAID SPECIFICALLY FOR THE LICENSE TO
THE SOFTWARE (IF ANY), OR (B) ONE HUNDRED U.S. DOLLARS (US$100).

Some jurisdictions do not allow certain limitations of liability; in those
cases, these limitations apply to the maximum extent permitted by law.

---

## 11. General

- These terms are governed by the laws of the jurisdiction where Atumera is
  organized, without regard to conflict‑of‑laws rules.
- Any dispute arising out of or relating to the Software or these terms will be
  resolved in the courts of that jurisdiction, and you consent to their
  personal jurisdiction.
- If any provision of these terms is found unenforceable, the remaining
  provisions will remain in full force and effect.
- Atumera may update these terms from time to time. Material changes will apply
  prospectively and, where practicable, will be noted in the repository
  changelog or documentation.

If you are negotiating a broader commercial or partner agreement with Atumera,
that agreement will govern to the extent it conflicts with this EULA.

