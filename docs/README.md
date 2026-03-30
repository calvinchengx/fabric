# Documentation (Fabric administrator scope)

**Start here:** [get-started.md](get-started.md) — install, configure **`.env`**, and run **`just health`**.

This folder describes how **Microsoft Fabric tenant administration** intersects with **`fabric-provisioner`**: which **Fabric admin portal** settings apply, what **Fabric Core REST** calls the app makes, and how we **operate** the provisioner safely.

## Reading this on GitHub

- Navigate to **`docs/`** in the repository. GitHub displays **`README.md`** (this file) below the file list—the same convention as the root **`README.md`**.
- Start with **[get-started.md](get-started.md)** (install, **`.env`**, first **`just health`**). Then open **[usage.md](usage.md)** for full examples, **[permissions.md](permissions.md)** for Entra/Fabric permissions, or **[architecture.md](architecture.md)** / **[governance.md](governance.md)** for design and policy; GitHub renders Markdown in the file view.
- Use the **Copy permalink** control on a file (or blame/history) when linking to a specific version of a paragraph from issues or PRs.

This folder is plain Markdown in git—no build step required for it to be readable on GitHub.

| Document | Contents |
|----------|----------|
| [**get-started.md**](get-started.md) | **Get started** — prerequisites, `just sync`, **`.env`**, **`just health`**, next steps |
| [**usage.md**](usage.md) | **How to run the tool** — **`just`**-first setup, CLI, HTTP, **`mkdocs`**, audit |
| [**permissions.md**](permissions.md) | **Entra + Fabric permissions**, **Mermaid diagrams** (gates, flows, identity split), least-privilege patterns |
| [architecture.md](architecture.md) | Entra vs Fabric split, Fabric APIs used (workspace create, **update workspace role assignment**, connections), tenant prerequisites **Fabric administrators** configure |
| [governance.md](governance.md) | Roles, operations, security, and checklists for Fabric workspaces and connections |
| [repository.md](repository.md) | Pointer to the root **README** (install, CLI, HTTP API) for GitHub Pages |

**Out of scope here:** Purview, non-Fabric Microsoft APIs, and other products—unless a link is needed for general org audit strategy.

Project setup and CLI: [repository.md](repository.md) · [root README on GitHub](https://github.com/calvinchengx/fabric/blob/main/README.md)

**GitHub Pages:** the site is built with **MkDocs** ([`mkdocs.yml` on GitHub](https://github.com/calvinchengx/fabric/blob/main/mkdocs.yml)). In the repository, open **Settings → Pages**, set **Build and deployment** source to **GitHub Actions**, merge the workflow, then use the URL shown on that page (see **[Documentation in the root README](https://github.com/calvinchengx/fabric/blob/main/README.md#documentation)**). **Local preview:** from the repo root, **`just docs`** (see **[CONTRIBUTING.md](https://github.com/calvinchengx/fabric/blob/main/CONTRIBUTING.md#short-commands-with-just)**).
