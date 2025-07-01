#!/usr/bin/env python3
"""
Setup script for Claude Code hooks integration with MCP MITM Mem0.

This script helps users configure hooks by:
1. Making hook scripts executable
2. Generating appropriate configuration
3. Providing installation instructions
"""

import json
import os
import stat
from pathlib import Path
from typing import Dict, Any


def make_scripts_executable():
    """Make all hook scripts executable."""
    hooks_dir = Path(__file__).parent
    scripts = [
        "memory_search.py", "memory_store.py", "memory_analyze.py", 
        "permission_intelligence.py", "session_context.py", "utils.py"
    ]
    
    print("Making hook scripts executable...")
    for script in scripts:
        script_path = hooks_dir / script
        if script_path.exists():
            # Add execute permission
            current_permissions = script_path.stat().st_mode
            script_path.chmod(current_permissions | stat.S_IEXEC)
            print(f"  ✓ {script}")
        else:
            print(f"  ✗ {script} not found")


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def generate_hook_config(template_name: str = "full_integration", custom_path: str = None) -> Dict[str, Any]:
    """Generate hook configuration for Claude Code."""
    
    # Load templates
    config_file = Path(__file__).parent / "config_templates.json"
    with open(config_file, 'r') as f:
        templates = json.load(f)
    
    if template_name not in templates["templates"]:
        print(f"Template '{template_name}' not found. Available templates:")
        for name, template in templates["templates"].items():
            print(f"  - {name}: {template['description']}")
        return {}
    
    config = templates["templates"][template_name]["config"].copy()
    
    # Update paths if custom path provided
    if custom_path:
        project_path = custom_path
    else:
        project_path = str(get_project_root())
    
    # Update all command paths in the configuration
    def update_command_paths(hook_config):
        if isinstance(hook_config, dict):
            if "command" in hook_config:
                # Replace the cd path in the command
                command = hook_config["command"]
                if "cd " in command and " && uv run python hooks/" in command:
                    parts = command.split(" && uv run python hooks/")
                    if len(parts) == 2:
                        hook_config["command"] = f"cd {project_path} && uv run python hooks/{parts[1]}"
            
            for key, value in hook_config.items():
                if isinstance(value, (dict, list)):
                    update_command_paths(value)
        elif isinstance(hook_config, list):
            for item in hook_config:
                update_command_paths(item)
    
    update_command_paths(config)
    return config


def display_installation_instructions(config: Dict[str, Any], template_name: str):
    """Display installation instructions for the user."""
    
    print(f"\n🎉 Hook configuration generated successfully using '{template_name}' template!\n")
    
    print("📋 INSTALLATION INSTRUCTIONS:")
    print("=" * 50)
    
    print("\n1. Choose your installation scope:")
    print("   • User-wide (all projects): ~/.claude/settings.json")
    print("   • Project-only: .claude/settings.json")
    print("   • Local development: .claude/settings.local.json")
    
    print("\n2. Add the following configuration to your chosen settings file:")
    print("-" * 50)
    print(json.dumps(config, indent=2))
    print("-" * 50)
    
    print("\n3. If the file already exists, merge the 'hooks' section with existing content.")
    
    print("\n4. Restart Claude Code or use '/hooks' command to verify configuration.")
    
    print("\n📝 TESTING:")
    print("   • Run a bash command and check for memory context")
    print("   • Use Ctrl-R to see hook execution progress")
    print("   • Check ~/.claude/hook_execution.log for execution logs")
    
    print("\n🔧 CUSTOMIZATION:")
    print("   • Modify 'matcher' fields to target specific tools")
    print("   • Adjust file paths if you moved the project")
    print("   • See config_templates.json for more options")


def create_sample_settings_files(config: Dict[str, Any]):
    """Create sample settings files for different scopes."""
    
    hooks_dir = Path(__file__).parent
    samples_dir = hooks_dir / "sample_configs"
    samples_dir.mkdir(exist_ok=True)
    
    # User settings sample
    user_config = {"hooks": config["hooks"]}
    with open(samples_dir / "user_settings.json", 'w') as f:
        json.dump(user_config, f, indent=2)
    
    # Project settings sample  
    project_config = {"hooks": config["hooks"]}
    with open(samples_dir / "project_settings.json", 'w') as f:
        json.dump(project_config, f, indent=2)
    
    print(f"\n📁 Sample configuration files created in: {samples_dir}")
    print("   • user_settings.json - Copy to ~/.claude/settings.json")
    print("   • project_settings.json - Copy to .claude/settings.json")


def main():
    """Main setup function."""
    print("🔧 MCP MITM Mem0 Hook Setup")
    print("=" * 40)
    
    # Make scripts executable
    make_scripts_executable()
    
    # Get user preferences
    print("\n📊 Available hook templates:")
    
    config_file = Path(__file__).parent / "config_templates.json"
    with open(config_file, 'r') as f:
        templates = json.load(f)
    
    for i, (name, template) in enumerate(templates["templates"].items(), 1):
        print(f"   {i}. {name}: {template['description']}")
    
    print("\nChoose a template (1-{}) or press Enter for full_integration: ".format(len(templates["templates"])), end="")
    
    try:
        choice = input().strip()
        if choice:
            choice_num = int(choice)
            template_names = list(templates["templates"].keys())
            if 1 <= choice_num <= len(template_names):
                template_name = template_names[choice_num - 1]
            else:
                template_name = "full_integration"
        else:
            template_name = "full_integration"
    except (ValueError, KeyboardInterrupt):
        template_name = "full_integration"
    
    print(f"\nUsing template: {template_name}")
    
    # Ask for custom path
    default_path = str(get_project_root())
    print(f"\nProject path (press Enter for '{default_path}'): ", end="")
    
    try:
        custom_path = input().strip()
        if not custom_path:
            custom_path = default_path
    except KeyboardInterrupt:
        custom_path = default_path
    
    # Generate configuration
    config = generate_hook_config(template_name, custom_path)
    
    if config:
        # Display instructions
        display_installation_instructions(config, template_name)
        
        # Create sample files
        create_sample_settings_files(config)
        
        print("\n✅ Setup completed! Follow the installation instructions above.")
    else:
        print("\n❌ Failed to generate configuration. Please check the template name.")


if __name__ == "__main__":
    main()