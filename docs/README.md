# MCP MITM Mem0 Documentation

Welcome to the comprehensive documentation for MCP MITM Mem0 - a simplified memory service for Claude that intercepts conversations via MITM proxy.

## 📚 Documentation Structure

### Core Documentation

- **[Architecture](architecture.md)** - System design, components, and technical architecture
- **[Onboarding](onboarding.md)** - Developer setup and getting started guide
- **[Deployment](deployment.md)** - Production deployment and service management
- **[Security](security.md)** - Security considerations, best practices, and threat model
- **[Dependencies](dependencies.md)** - Package management, updates, and maintenance

### Architecture Decision Records (ADRs)

The `adr/` directory contains Architecture Decision Records documenting significant technical decisions:

- **[0001 - Record Architecture Decisions](adr/0001-record-architecture-decisions.md)** - Decision to use ADRs for documentation

Future ADRs will document decisions about:
- Technology stack choices (MITM proxy, Mem0 SaaS)
- Architecture patterns (async processing, error handling)
- Integration approaches (MCP protocol, API design)

## 🚀 Quick Start

New to the project? Start here:

1. **[Onboarding Guide](onboarding.md)** - Complete setup instructions
2. **[Architecture Overview](architecture.md#overview)** - Understand the system
3. **[Deployment Guide](deployment.md)** - Get it running
4. **[Security Guide](security.md)** - Configure safely

## 🔧 For Developers

### Getting Started
- Follow the **[Onboarding Guide](onboarding.md)** for complete setup
- Review **[Architecture](architecture.md)** to understand the system design
- Check **[Dependencies](dependencies.md)** for package management details

### Contributing
- Read **[Architecture Decisions](adr/)** to understand past choices
- Follow security best practices from **[Security Guide](security.md)**
- Ensure proper testing as outlined in **[Onboarding](onboarding.md#testing)**

## 🛡️ For Operators

### Deployment
- Follow **[Deployment Guide](deployment.md)** for production setup
- Review **[Security Guide](security.md)** for hardening
- Set up monitoring as described in **[Deployment - Monitoring](deployment.md#monitoring-and-logging)**

### Maintenance
- Regular tasks in **[Dependencies - Maintenance](dependencies.md#maintenance)**
- Security updates from **[Security - Best Practices](security.md#best-practices)**
- Health monitoring from **[Deployment - Health Monitoring](deployment.md#health-monitoring)**

## 📋 Documentation Standards

This documentation follows industry best practices:

- **Architecture**: Based on Google's architecture documentation template
- **ADRs**: Follow MADR (Markdown Architecture Decision Records) format
- **Onboarding**: Developer-focused with practical setup steps
- **Security**: Comprehensive threat model and mitigation strategies
- **Deployment**: Production-ready with service management

## 🔄 Keeping Documentation Current

Documentation is maintained alongside code changes:

- **Architecture changes** → Update architecture.md and create ADR
- **New dependencies** → Update dependencies.md
- **Security changes** → Update security.md and deployment.md
- **API changes** → Update onboarding.md and architecture.md

## 📖 Related Resources

### External Documentation
- **[Mem0 Documentation](https://docs.mem0.ai/)** - Memory service API
- **[MCP Protocol](https://modelcontextprotocol.io/)** - Model Context Protocol specification
- **[mitmproxy Documentation](https://docs.mitmproxy.org/)** - Proxy setup and configuration

### Project Resources
- **[Main README](../README.md)** - Project overview and quick start
- **[pyproject.toml](../pyproject.toml)** - Project configuration and dependencies
- **[Tests](../tests/)** - Test suite for understanding behavior

## 💡 Documentation Tips

- **Search**: Use your editor's search across files to find specific topics
- **Links**: Follow internal links between documents for related information
- **Examples**: All guides include practical examples and commands
- **Updates**: Check document headers for "Last Updated" dates

## 🆘 Getting Help

If you can't find what you're looking for:

1. **Search** the documentation using your editor
2. **Check** the main [README](../README.md) for overview information
3. **Review** relevant [test files](../tests/) for usage examples
4. **Open** an issue on GitHub for missing documentation

---

*This documentation is maintained as part of the MCP MITM Mem0 project. For the most current information, always refer to the version in the main branch.* 