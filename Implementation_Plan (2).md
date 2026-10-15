# Implementation Plan — Universal Linux Application Manager

> **Instructions for the AI coding agent:** Read this file completely before making changes. Treat it as the project’s source of truth. If persistent project memory is available, save a concise, durable summary of the goals, architecture, safety rules, design direction, compatibility requirements, and current progress before starting implementation. Keep that memory up to date as decisions change. Do not merely acknowledge this plan: inspect the environment and repository, then execute it in small, verifiable stages.

## 1. Project mission

Build a polished, trustworthy, open-source desktop application for Linux that gives users one clear place to discover, inspect, filter, launch (where appropriate), and uninstall applications installed through **different installation methods**, regardless of Linux distribution.

The primary development and test environment is **Fedora**, but Fedora must not be hard-coded as the only supported distribution. The architecture and release process should aim to support Ubuntu, Debian, Linux Mint, Pop!_OS, Arch Linux, Manjaro, openSUSE, and other distributions where the relevant package tools and desktop capabilities are available.

The application should help ordinary users answer:
- What applications are installed on this computer?
- What version is each application, where did it come from, where is it installed, and is it a system-wide or per-user installation?
- Which installation method was used: Flatpak, Snap, AppImage, the distribution’s native package manager, or another/unknown source?
- What exactly will be removed if I uninstall an entry, and will its personal data be kept?

**Working product name:** use a temporary, memorable name in code and documentation, but keep the name configurable until a final name is chosen. Do not copy another product’s branding.

## 2. Non-negotiable requirements

1. **One inventory, multiple sources.** Collect discoverable applications from all supported providers and present them in one unified interface.
2. **Accurate source labels.** Do not pretend every application has a known installation source. Show `Unknown` when provenance cannot be established reliably.
3. **Separate source from scope.** Source describes the packaging/installation mechanism; scope describes whether the installation is system-wide or user-scoped. These are different attributes and may overlap.
4. **Safe, explicit removal.** Never silently execute destructive actions, remove personal data by default, or run arbitrary shell strings. Every uninstall operation must identify its precise target and explain important consequences before the user confirms.
5. **Cross-distribution architecture.** Use capability detection and provider adapters; do not assume `dnf`, `apt`, `pacman`, `zypper`, or any single manager exists everywhere.
6. **No false promise of universal detection.** Document what can and cannot be found. Support the broadest practical coverage through an extensible provider system and report incomplete scans clearly.
7. **High-quality UI/UX.** Do not ship a default-looking CRUD/admin dashboard. Use a coherent, intentional design system and polished interaction details.
8. **Avoid blue and purple as the main visual palette.** Pick a distinctive alternative such as warm graphite/ivory with restrained amber, orange, terracotta, or lime accents. Keep contrast and accessibility more important than decoration.
9. **Open-source ready.** Include licensing, contribution guidance, issue templates, reproducible build instructions, automated tests, CI, and release packaging guidance.
10. **Test before claiming support.** Distinguish “implemented,” “tested in CI,” “tested on a real distribution,” and “not yet verified.”

## 3. First action: inspect the environment and design skills

Before committing to a UI direction or writing significant UI code:

1. Inspect the current repository, runtime, operating system, desktop environment, available build tools, and the AI coding environment. Preserve useful existing work; do not replace or restructure a repository blindly.
2. Look for installed agent skills/design tools and read their usage instructions. Prioritize **UI/UX Pro Max** (often distributed through `ui-ux-pro-max-cli`) or the equivalent skill supported by the current agent. Official/reference starting points:
   - CLI package: https://www.npmjs.com/package/ui-ux-pro-max-cli
   - Skill repository: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
   - CLI documentation: https://ui-ux-pro-max-skill.com/docs/cli-reference/
3. Verify the current installation command and supported AI-agent target from the tool’s current documentation before running it. Do not assume every coding agent uses the same target name. A documented pattern has been `npm install -g ui-ux-pro-max-cli` followed by `uipro init --ai <agent>`, but verify that this is still correct for the installed package/version and this particular agent. Prefer a safe, non-global or project-local option when supported.
4. If a required design skill is missing, cannot be installed in the current environment, has an incompatible agent target, or requires permissions that the agent does not have, **tell the user exactly what is missing and ask them to install/enable it before proceeding with substantial UI implementation**. Include the official link and the verified installation instructions. Do not claim that a skill was used when it was not. You may continue with non-visual research, architecture, and tests while the design dependency is blocked, but clearly mark the UI implementation as blocked pending the user’s response.
5. Once available, use the skill actively to generate/review design-system choices, layout, typography, spacing, component states, responsive behavior, and accessibility. Do not simply mention the skill in a commit message. If the skill provides a search/design-system workflow, run it and preserve useful results in project documentation (for example, `docs/design-system.md`).
6. If UI/UX Pro Max is unavailable and the user chooses not to install it, propose a documented fallback using available, reputable design/accessibility tools or existing project capabilities. Get the required user decision rather than silently substituting a weaker process.

## 4. Discovery and architecture decision record

After repository/environment inspection, create `docs/architecture.md` and record:

- Chosen language, GUI framework, packaging strategy, and why they fit Linux desktop integration and long-term maintenance.
- How privileged package operations are invoked securely.
- The provider interfaces and capability-detection approach.
- Supported and unsupported distributions/package formats.
- The UI design system and selected visual direction.
- Threat model and data-deletion policy.
- Known limitations and decisions that may need revisiting.

Choose a **maintainable desktop-native or desktop-appropriate GUI stack** that works reliably on the target Linux distributions. Evaluate packaging portability, accessibility, dark/light theme support, keyboard navigation, process management, and maintainability before locking in the stack. Do not choose a framework just because it is familiar. Prefer a small, testable backend with well-separated inventory adapters and a frontend that can be iterated on independently.

Do not require an internet connection for routine local inventory or uninstalling. Do not upload installed-app lists, file paths, hardware information, or user data to a remote service.

## 5. Application information model

Represent each discovered installation as an **installation record**, not merely a unique application name. The same application may legitimately exist as a Flatpak and a native package, or in multiple scopes/branches. Do not merge these into one ambiguous record.

A record should contain fields when available:

- Stable internal record ID.
- Display name and package/application identifier.
- Version and architecture.
- Source/provider: `Flatpak`, `Snap`, `AppImage`, `RPM`, `DEB/APT`, `Pacman`, `Zypper`, `APK`, `Portage`, another known provider, or `Unknown`.
- Scope: `System`, `User`, or `Unknown`.
- Installation origin/remote/repository where available.
- Executable or launch target where safely discoverable.
- Desktop-entry path and application icon where available.
- Actual installation path or package identity.
- Installed size only when trustworthy; do not invent sizes. Distinguish package size, installed size, and estimated file size.
- Install date only when reliable; otherwise omit it.
- Whether administrator permission is required to remove it.
- Whether user data may exist and what the removal operation preserves/deletes.
- Confidence and provenance metadata for detected fields.
- Provider capabilities and known warnings.

Keep raw provider IDs/refs separate from display labels. Never form shell commands by interpolating display names or other untrusted values.

## 6. Inventory categories and filters

The interface must provide the requested prominent filters:

- **All** — every discovered application installation.
- **Flatpak**
- **Snap**
- **AppImage**
- **System** — installations whose scope is system-wide, regardless of source.
- **User** — installations scoped to the current user.
- **Unknown** — the source, scope, or both cannot be established confidently. Clearly indicate which part is unknown.

These filters intentionally overlap: for example, a system-scoped Flatpak should appear under both `Flatpak` and `System`. Make this behavior intuitive and document it in help text or tooltips.

Add useful search and sorting: name, package ID, source, scope, and version where supported. Useful sort modes include alphabetical order, source, and size (only when size data is trustworthy). Add optional filters for duplicate installations, removable status, and applications requiring administrator permission.

Create a clear distinction between **desktop applications** and the underlying packages/libraries needed by the OS. Keep libraries, runtimes, services, drivers, kernels, and essential components hidden from the normal application view by default when they can be classified reliably. Offer an explicit advanced inventory mode if the project decides to expose them. Never imply that every installed package is a standalone GUI app.

## 7. Provider architecture and coverage

Use a modular provider/adapter interface. Each provider should report:

- Availability and version of the relevant tool.
- Whether inventory discovery is supported.
- Whether metadata such as scope, size, and origin is available.
- Whether safe uninstall is supported.
- Whether removal requires elevation.
- Structured errors, partial results, and actionable diagnostic information.

One broken or missing provider must not prevent other providers from displaying their results. Run discovery without elevation whenever possible. Avoid long freezes: use asynchronous/background tasks, progress state for slower scans, cancellation where practical, and a refresh action.

### Initial provider priorities

Implement and test these in order, based on what is available on the host:

1. **Native distribution package managers**
   - Fedora/RHEL-family: RPM plus the installed frontend where relevant (`dnf`/`dnf5` and compatible RPM tooling).
   - Debian/Ubuntu-family: `dpkg` and APT metadata.
   - Arch-family: `pacman`.
   - openSUSE: RPM plus `zypper` as appropriate.
   - Other providers can be added through the adapter interface, such as Alpine (`apk`) and Gentoo (`emerge`/Portage), after the core adapters are stable.
   - Do not equate “the command exists” with “this manager owns every installed app.” Detect distribution identity as a hint, then detect actual executable capabilities.
2. **Flatpak**
   - Inventory user and system installations separately.
   - Preserve app IDs, refs, branch/architecture, installation location, and remote when reported.
   - Distinguish applications from runtimes.
3. **Snap**
   - Inventory installed snaps and retain exact snap names/revisions/channel information when available.
   - Explain data/snapshot consequences before removal and respect the package manager’s supported semantics.
4. **AppImage**
   - Discover likely AppImage files in reasonable, documented locations, including common user application directories and desktop entries that point to AppImages.
   - Avoid scanning the entire filesystem by default. Allow users to add folders and rescan them.
   - Identify AppImages using reliable file/metadata inspection where possible; do not execute unknown AppImages just to inspect them.
   - Use AppImage desktop-integration metadata where available. AppImages are often portable files rather than package-manager registrations, so detection may be incomplete.
5. **User-installed or manually installed applications**
   - Inspect user desktop entries, common user application folders, and other low-risk integration points.
   - Use desktop-entry `Exec` and related metadata conservatively. Parse/inspect it; do not run it during scanning.
   - Recognize that manually installed executables, scripts, source builds, language-specific package ecosystems, containerized apps, and files placed in arbitrary directories cannot always be classified automatically.
6. **Unknown / future providers**
   - Keep a generic provider interface so new formats can be added without rewriting the UI.
   - Display unknown entries only when evidence supports treating them as applications. State the evidence and avoid inventing an uninstall command.

Do not promise that the tool can reliably uninstall “anything from any source.” Make the honest goal: **maximum discoverability with a safe, evidence-based uninstall path whenever one is available**.

## 8. Uninstall workflow and safety rules

Uninstalling is the highest-risk operation in this application. Implement it as a separate, well-tested service rather than as button-specific UI logic.

### Required flow

1. User selects an installation and chooses **Uninstall**.
2. Show a confirmation dialog with application name, source, scope, exact target/identifier, whether admin authorization is needed, and what will be removed.
3. Explain data handling separately from package removal. Default to **preserving personal configuration/data** whenever the provider supports that choice.
4. If the user chooses to delete associated application data, show the exact known paths or a plain-language summary, distinguish confirmed paths from estimates, and require an explicit opt-in. Do not delete unrelated files.
5. Where package-manager dependencies or other packages may also be removed, show the package manager’s proposed transaction/summary when possible, and allow cancellation before applying it.
6. Ask for fresh authorization through the operating system’s supported privilege/authentication mechanism when needed. Never ask the user to paste a password into the app, save a password, run the entire GUI as root, or silently invoke an authentication bypass.
7. Execute only the provider-specific operation with structured arguments; report success, partial success, cancellation, or failure accurately. Refresh the inventory after the operation.
8. Write a minimal local activity/history entry if enabled; avoid storing sensitive command output or unnecessary paths. Make history clearable.

### Security rules

- Never execute a dynamically constructed shell command. Prefer safe process APIs with argument arrays, strict validation, timeouts, bounded output, and appropriate cancellation.
- Never use `sudo` as a generic wrapper or start the whole graphical app with root privileges. Use the package manager’s normal authorization flow or a small, narrowly scoped helper/Polkit mechanism if the chosen stack requires it.
- No arbitrary `rm -rf`, wildcard deletion, or guessed cleanup paths.
- For AppImages, uninstalling should default to moving/removing only the selected file after confirmation, plus clearly identified desktop integration artifacts only when the user opts in. Never recursively delete a parent folder or remove every file with a similar name.
- For Flatpak, explain the difference between removing the app and deleting its per-app data. Keep data by default; the delete-data option must be explicit. Follow current Flatpak semantics and test them.
- For Snap, explain the relevant removal and retained-data/snapshot behavior; do not silently choose a purge operation.
- For native packages, use the system package manager so dependency checks and authorization remain under its control. Never force-remove dependencies by default.
- Unknown entries without a reliable target/provider should have no enabled one-click uninstall action. Offer “Show location/details” or guided manual instructions instead.
- Detect or warn about protected/critical system components, including core OS, package-management, boot, desktop-session, and essential networking components when reliably identifiable. The normal application view must not offer casual one-click removal for them. An advanced workflow, if provided, must make the risk clear and require typed confirmation; do not bypass package-manager protections.
- Treat provider output, filenames, desktop-entry data, metadata, and package names as untrusted input.
- Never report an item as deleted unless the provider confirms the operation completed and a fresh scan supports the result.

### Undo and recovery

Do not promise undo unless a provider offers a tested rollback method. Explain that ordinary native package uninstalls may not be reversible. Where feasible, offer a clear pre-removal summary and optionally let users export it for troubleshooting.

## 9. UI/UX and visual design brief

The app should feel like a thoughtfully designed, modern Linux utility, not a generic website transplanted into a desktop window.

### Visual direction

- **No purple/blue-led theme.** Explore a warm, distinctive palette: charcoal or warm near-black surfaces, soft ivory/light neutral surfaces, and a restrained amber/orange/terracotta/lime accent. Make semantic warning/error/success colors accessible and consistent.
- Use intentional typography, a strong hierarchy, generous but efficient spacing, tidy iconography, consistent corner radii, precise alignment, and a small reusable component system.
- Avoid excessive gradients, glowing borders, glassmorphism, meaningless charts, oversized hero areas, and unnecessary decoration.
- Make the main inventory immediately useful: app icon/name, concise secondary identifier when needed, clear source/scope chips, version if available, and an obvious but not dangerously prominent action menu.
- Provide polished light and dark themes if practical with the chosen framework, honoring the host desktop’s preference where supported.
- Use realistic data in mockups and previews. Do not hard-code demo data into production inventory logic.

### Layout and interaction requirements

- A clear navigation/filter area for All, Flatpak, Snap, AppImage, System, User, and Unknown.
- A main list or grid with adjustable density if the framework allows it. Default to a scannable list/table-like inventory suitable for hundreds of applications.
- Search should be easy to find and keyboard accessible.
- Sort, refresh, and rescan controls must be discoverable.
- Empty, loading, partial-scan, permission-needed, error, and no-results states must all be designed intentionally.
- Show source and scope as separate fields rather than ambiguous combined labels.
- Detail view/panel should expose identifiers, installation path, origin, metadata confidence, and removal consequences.
- Confirmation dialogs must be calm, plain-language, and specific; warnings should be proportional to actual risk.
- Include keyboard navigation, accessible labels, visible focus, screen-reader semantics, sufficient contrast, scalable text, and sensible behavior at smaller window sizes.
- Do not use color alone to convey meaning. Icons/chips must have text or accessible labels.
- Use consistent notifications/toasts for scan completion and uninstall results, with a route to error details when relevant.
- Provide a “Report a detection issue” path that collects only user-approved, minimal diagnostic information.

### Required design outputs

Before building out the full UI, produce or document:

1. A concise design-system definition (`docs/design-system.md`) covering palette, typography, spacing, sizing, icons, elevation, component states, and accessibility decisions.
2. Main-window layout and key interaction flow.
3. Inventory-row/card, filter, search, details, uninstall-confirmation, empty state, scan error, and critical-component warning designs.
4. The reasoning behind major UI choices based on user tasks, not personal aesthetic preference alone.

Use the available UI/UX skill during these activities. Iterate after rendering/running the actual app; do not stop at a mockup.

## 10. Suggested code organization

Adapt this to the actual language/framework, but preserve the separation of responsibilities:

- `app/` or equivalent: window lifecycle and application entry point.
- `ui/`: views, reusable components, states, navigation, design tokens.
- `domain/`: application-installation model, source/scope enums, capabilities, operation results.
- `providers/`: one adapter per provider/package manager.
- `inventory/`: provider orchestration, normalization, deduplication rules, scanning progress, cache invalidation.
- `uninstall/`: plan generation, safety checks, confirmation data, authorization integration, execution, result verification.
- `system/`: OS/capability detection, safe process wrapper, desktop-entry parsing, file metadata utilities.
- `tests/`: unit, integration, security, UI, and packaging tests.
- `docs/`: architecture, design system, supported formats/distributions, threat model, troubleshooting, contribution guide.

Use typed result/error structures instead of string parsing scattered throughout the UI. Providers should return structured records and capabilities. Keep platform-specific code isolated.

## 11. Internationalization and accessibility

- Structure visible strings so localization can be added without rewriting UI logic.
- Use English as the first locale unless the repository already establishes another policy.
- Do not assume every path, username, package name, or application name is ASCII.
- Handle Unicode filenames, spaces, newlines in paths, localization, right-to-left expansion, and long names defensively.
- Follow desktop accessibility conventions and test keyboard-only operation.

## 12. Testing strategy

Create automated tests from the beginning, not after implementation.

### Unit tests

- Source/scope classification, including overlapping filters.
- Provider parsing with realistic fixtures for multiple package-manager versions and locales where relevant.
- Unknown/missing metadata and partial provider failures.
- Multiple installations of the same app without accidental merging.
- Desktop-entry parsing and AppImage identification without executing the application.
- Argument construction, validation, quoting/path edge cases, and untrusted metadata handling.
- Removal plans and preservation/deletion of data under each provider’s policy.
- Protected/critical-package guard behavior.

### Integration and safety tests

- Use mocked executables or isolated test environments; never run destructive package removal against the developer’s host during tests.
- Test absent tools, permission denial, cancellation, slow/hung processes, malformed output, non-zero exit codes, and interrupted operations.
- Confirm no provider failure hides results from other providers.
- Confirm unknown targets cannot trigger guessed shell commands or file deletion.
- Verify refresh and result reporting after successful and unsuccessful operations.

### UI/UX tests

- First launch, loading, empty inventory, successful scan, partial scan, search/filter combinations, duplicate installations, app details, confirmation/cancel paths, errors, dark/light themes, narrow windows, and keyboard navigation.
- Check typography, alignment, spacing, contrast, focus indicators, and text scaling in a running build.

### Distribution matrix

- Test first on the developer’s Fedora environment.
- Add CI/build checks for the chosen packaging formats and more distributions where feasible.
- Use disposable virtual machines or containers for integration testing when the package-manager operation can be safely isolated. Clearly note that containers do not perfectly reproduce desktop/session behavior.
- Maintain a documented support matrix distinguishing discovery, details, and uninstall support for each provider and distribution.

## 13. Linux release and packaging strategy

Design releases for real users, not only the developer’s Fedora machine. Choose a sensible set of distributable artifacts based on framework support and testability, which may include:

- A native Fedora/RPM package.
- A Debian/Ubuntu `.deb` package.
- An AppImage for portable distribution if compatible with the selected stack and its dependencies.
- Flatpak packaging and a Flathub submission path if appropriate.
- Other packages such as Arch/AUR or openSUSE builds only when maintainable and verifiable.

Do not claim one artifact will work on literally every Linux system. For each artifact, document supported architectures, runtime requirements, installation/uninstallation steps, update behavior, and known limitations. Avoid bundling or executing privileged helpers without a reviewed security design. Never bundle distribution package managers into the app.

Add a release checklist for clean-install testing, upgrade testing, uninstall testing, checksums, versioning, changelog, signatures where practical, and artifact verification.

## 14. GitHub open-source plan

Prepare the repository for public contribution. Include at minimum:

- `README.md`: purpose, screenshots, feature list, supported providers/distributions, installation methods, limitations, safety model, status, and how to report bugs.
- `LICENSE`: recommend a permissive license such as MIT or Apache-2.0 only after checking dependency compatibility and the project’s intended contribution model. Do not publish without an explicit, appropriate license.
- `CONTRIBUTING.md`: development setup, test commands, style guidelines, branch/PR expectations, and how to add a provider.
- `CODE_OF_CONDUCT.md` and `SECURITY.md` with an appropriate vulnerability-reporting path.
- `CHANGELOG.md` or a release-note convention.
- Issue templates for bug reports, feature requests, provider-support requests, and detection inaccuracies.
- Pull-request template.
- CI workflows for linting, tests, build checks, dependency/security checks where practical, and release artifacts.
- A support matrix and explicit rules for collecting diagnostic information.
- Screenshots/GIFs made from the real application, with no personal paths or sensitive machine details.

Before public release:

1. Search the chosen project name for collisions and avoid names that imply official affiliation with a Linux distribution or package format.
2. Review dependencies, licenses, bundled assets, fonts, icons, and third-party notices.
3. Ensure logs and bug-report templates do not expose usernames, home-directory paths, hostnames, or installed-software inventories without explicit user consent.
4. Test installation and removal of each release artifact on a clean test system.
5. Publish versioned GitHub Releases with clear notes, verified checksums, and known limitations.
6. Document how users can contribute additional package-provider adapters and tests.

The agent should prepare all source files and release workflows, but must not publish to a remote GitHub repository, create a public release, or upload machine/user data unless the user explicitly authorizes the action and supplies/has configured the required repository access.

## 15. Development phases and deliverables

Execute in small increments and keep the project runnable at each milestone.

### Phase 0 — Environment, repository, and skill readiness

- Inspect repository and environment.
- Verify UI/UX Pro Max or another agreed design skill is installed and usable with the active agent.
- If it is not usable, request user action as described in Section 3 before substantial UI implementation.
- Record assumptions and create an implementation checklist.

**Exit criteria:** confirmed stack options, design skill status, existing repository state, and a written list of decisions/risks.

### Phase 1 — Architecture and security design

- Create architecture, threat model, provider interface, data model, and uninstall policy documents.
- Define the support matrix and reliable capability-detection strategy.
- Decide on privilege elevation and error-handling architecture.

**Exit criteria:** the design explains how inventory and uninstall are kept separate, how privileged operations work, and how unknown targets are handled safely.

### Phase 2 — Inventory foundation

- Implement typed installation records, provider interface, structured process execution, detection/capabilities, and scan orchestration.
- Add fixtures and unit tests.
- Keep provider failure isolated and visible.

**Exit criteria:** fake providers and available read-only providers can populate one normalized inventory with source/scope filters behaving correctly.

### Phase 3 — Priority providers

- Implement the core provider list in Section 7, beginning with the current Fedora host and then portable adapters.
- Add metadata confidence and partial-scan UI feedback.
- Add duplicate-installation handling and AppImage/desktop-entry discovery.

**Exit criteria:** installed applications are accurately reported on the Fedora development host; each supported provider has fixtures and documented gaps.

### Phase 4 — Design system and UI implementation

- Use the UI/UX skill to define the design system and key views.
- Implement filters, search, sorting, details, scan status, empty/error states, theme support, and keyboard/accessibility behavior.
- Run and inspect the actual app; iterate on visual issues.

**Exit criteria:** the real running app meets the brief in Section 9 and does not rely on static mock data.

### Phase 5 — Safe uninstall implementation

- Implement provider-specific plan/confirm/execute/verify flow.
- Integrate OS authorization correctly.
- Preserve data by default; make additional data deletion explicit.
- Add critical-component guards, cancellation, detailed but privacy-conscious errors, and post-action refresh.

**Exit criteria:** mock-based safety tests cover both success and failure paths, and no destructive action can start without an explicit confirmation tied to the exact target.

### Phase 6 — Packaging, compatibility, and CI

- Build distributable artifacts and CI.
- Test clean installs, upgrades, uninstall of the app itself, desktop integration, and supported architectures.
- Update the distribution/provider matrix with what was actually tested.

**Exit criteria:** each published artifact has reproducible build instructions and documented test status.

### Phase 7 — Open-source readiness

- Complete documentation, license, contribution/security files, issue templates, CI, screenshots, and release checklist.
- Run a privacy/security review and a final clean-environment test.
- Present the user with a summary of completed work, known gaps, local test results, and proposed first GitHub release steps.

**Exit criteria:** the repository can be published intentionally by the user, with no secrets, user data, or false compatibility claims.

## 16. Working rules for the coding agent

- Work incrementally and run tests after each meaningful change.
- Inspect files before editing them. Do not overwrite user work without understanding it.
- Do not claim an implementation, provider, design skill, test, or distribution is complete unless verified.
- When a decision is reversible and low-risk, make a reasonable choice and record it instead of interrupting the user repeatedly.
- Ask the user only when needed for a real blocker, destructive/high-impact decision, unavailable required design skill, license/repository publication choice, or permission that only the user can grant.
- Never perform privileged or destructive system actions on the user’s real machine as part of development tests.
- Prefer official upstream documentation for package-manager semantics, and re-check those details when implementing provider behavior.
- Keep dependencies minimal, maintained, and license-compatible.
- Avoid telemetry by default. Any optional telemetry must be documented, consent-based, and disabled by default unless the user explicitly approves a different policy.
- Maintain a concise project progress section in `docs/implementation-status.md`, including completed work, next tasks, test results, verified platforms, and known limitations. Update persistent agent memory if the environment supports it.
- Do not stop after generating plans and mockups: implement the working application and verify it within the capabilities and permissions of the environment.

## 17. Definition of done

The project is ready for its first public release only when:

- Users can scan and view applications from multiple supported sources in one interface.
- The All, Flatpak, Snap, AppImage, System, User, and Unknown filters behave consistently and transparently.
- Source and scope are separate, accurate fields, and duplicate installations are not silently merged.
- Inventory remains useful when some managers are absent or fail.
- The UI has been built and visually reviewed in a running app using the agreed design skill or an explicitly agreed fallback.
- Uninstall is provider-specific, target-specific, cancellable, authorization-aware, and data-preserving by default.
- Unknown or unsafe targets cannot trigger arbitrary commands or guessed deletion paths.
- Tests cover parsing, errors, failure isolation, uninstall safety, and key UI states.
- The project has clear documentation for supported providers and real test coverage, packaging/build instructions, a license, and GitHub contribution/security basics.
- Release notes state known limitations and do not claim untested “all Linux” compatibility.

## 18. Reference documentation

Start with official or project-maintained sources and verify command behavior against the installed versions. These links are starting points, not substitutes for version-specific testing:

- UI/UX Pro Max CLI package: https://www.npmjs.com/package/ui-ux-pro-max-cli
- UI/UX Pro Max skill repository: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- UI/UX Pro Max CLI reference: https://ui-ux-pro-max-skill.com/docs/cli-reference/
- Flatpak documentation: https://docs.flatpak.org/en/latest/using-flatpak.html
- Flathub uninstall guidance: https://docs.flathub.org/docs/for-users/uninstallation
- Snap documentation: https://snapcraft.io/docs/tutorials/get-started/
- AppImage user guide: https://docs.appimage.org/user-guide/
- AppImage desktop integration: https://docs.appimage.org/reference/desktop-integration.html

**Final instruction:** Prioritize correctness, safety, extensibility, and a genuinely excellent user experience. The goal is not merely to list package names; it is to help a Linux user understand what is installed and remove the intended application safely, with no hidden destructive behavior.
