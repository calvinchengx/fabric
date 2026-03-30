# Documentation (Fabric administrator scope)

This folder describes how **Microsoft Fabric tenant administration** intersects with **`fabric-provisioner`**: which **Fabric admin portal** settings apply, what **Fabric Core REST** calls the app makes, and how we **operate** the provisioner safely.

## Reading this on GitHub

- Navigate to **`docs/`** in the repository. GitHub displays this **`README.md`** automatically below the file list (the same pattern as the root **`README.md`**).
- Open **[ARCHITECTURE.md](ARCHITECTURE.md)** or **[GOVERNANCE.md](GOVERNANCE.md)** for the full pages; GitHub renders Markdown in the file view.
- Use the **Copy permalink** control on a file (or blame/history) when linking to a specific version of a paragraph from issues or PRs.

This folder is plain Markdown in git—no build step required for it to be readable on GitHub.

| Document | Contents |
|----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Entra vs Fabric split, Fabric APIs used, tenant prerequisites **Fabric administrators** configure |
| [GOVERNANCE.md](GOVERNANCE.md) | Roles, operations, security, and checklists for Fabric workspaces and connections |
| [repository.md](repository.md) | Pointer to the root **README** (install, CLI, HTTP API) for GitHub Pages |

**Out of scope here:** Purview, non-Fabric Microsoft APIs, and other products—unless a link is needed for general org audit strategy.

Project setup and CLI: [repository.md](repository.md) · [root README on GitHub](https://github.com/calvinchengx/fabric/blob/main/README.md)

**GitHub Pages:** the site is built with **MkDocs** ([`mkdocs.yml` on GitHub](https://github.com/calvinchengx/fabric/blob/main/mkdocs.yml)). In the repository, open **Settings → Pages**, set **Build and deployment** source to **GitHub Actions**, merge the workflow, then use the URL shown on that page (see **[Documentation in the root README](https://github.com/calvinchengx/fabric/blob/main/README.md#documentation)**).
