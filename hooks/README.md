# Claude Code Hooks for MCP MITM Mem0

This directory contains Claude Code hooks that provide **deterministic memory integration** - ensuring Claude always has access to relevant context and automatically captures learning without relying on autonomous decision-making.

## 🎯 What This Solves

Without hooks, our memory system relies on Claude **choosing** to use MCP tools:
- ❌ Claude might forget to check memories
- ❌ Important solutions might not get stored  
- ❌ Patterns might go unrecognized
- ❌ Context might be lost between sessions

With hooks, memory operations happen **automatically**:
- ✅ Relevant memories surface before every operation
- ✅ Successful outcomes are automatically stored
- ✅ Patterns are analyzed after each session
- ✅ Context is never lost

## 📁 Hook Scripts

### `memory_search.py` (PreToolUse Hook)
**Purpose**: Search memories before tool execution to provide relevant context

**Triggers**: Before Bash, Edit, Write, Task, and MCP tool operations
**Benefits**: 
- Prevents repeating solved problems
- Surfaces relevant past solutions
- Blocks operations that have repeatedly failed
- Provides context for file modifications

### `memory_store.py` (PostToolUse Hook)  
**Purpose**: Automatically store successful outcomes and solutions

**Triggers**: After successful Bash, Edit, Write, Task operations
**Benefits**:
- Captures solutions without Claude needing to remember
- Builds knowledge base of successful approaches
- Stores project context and preferences
- Creates searchable history of work

### `memory_analyze.py` (Stop Hook)
**Purpose**: Analyze conversation patterns when Claude finishes responding

**Triggers**: When Claude stops responding (session end)
**Benefits**:
- Identifies recurring issues automatically
- Surfaces incomplete projects
- Generates insights about user patterns
- Improves future assistance

### `permission_intelligence.py` (Notification Hook)
**Purpose**: Provide intelligent context when Claude requests permission for operations

**Triggers**: When Claude shows permission/notification dialogs
**Benefits**:
- Warns about risky operations based on past failures
- Surfaces relevant context for permission decisions
- Prevents repeated mistakes by showing past issues
- Provides confidence when operations have worked before

### `session_context.py` (Stop Hook)
**Purpose**: Automatically load relevant project and session context at session start

**Triggers**: When starting new sessions (stop_hook_active=False)
**Benefits**:
- Immediately provides project context and recent work
- Surfaces incomplete projects and ongoing issues
- Loads relevant preferences and decisions
- Ensures continuity between sessions

### `pre_response_hook.py` (PreResponse Hook)
**Purpose**: Detect error patterns in Claude's responses and inject prevention suggestions

**Triggers**: Before Claude's responses are displayed to the user
**Benefits**:
- Detects potential errors before they occur
- Injects prevention suggestions based on past solutions
- Learns from similar errors in memory
- Provides proactive guidance to avoid repeated mistakes

### `project_continuity_hook.py` (Notification Hook)
**Purpose**: Track project state and maintain continuity across sessions

**Triggers**: On conversation start/end notifications
**Benefits**:
- Captures project state (files modified, commands run, current tasks)
- Stores state for next session continuation
- Provides previous project context at session start
- Ensures seamless project handoffs between sessions

### `auto_reflection_hook.py` (PostToolUse/PreResponse Hook)
**Purpose**: Automatically trigger reflection based on conversation complexity and patterns

**Triggers**: After tool use or before responses when thresholds are met
**Benefits**:
- Triggers reflection after 20 messages, 3 errors, or 15 tool uses
- Analyzes conversation complexity to determine reflection needs
- Stores reflection insights as special memories
- Resets counters after successful reflection

### `memory_curation_hook.py` (PostToolUse Hook)
**Purpose**: Enhance stored memories with metadata for better retrieval

**Triggers**: After memories are stored (mcp__memory__add_memory)
**Benefits**:
- Automatically categorizes memories (error_solution, configuration, etc.)
- Extracts entities (filenames, commands, error types)
- Links related memories together
- Adds search keywords and tags for improved retrieval

### `utils.py`
**Purpose**: Common functionality shared by all hooks

**Features**:
- JSON I/O handling for hook communication
- Memory service interface functions
- Error handling and logging
- Helper functions for content analysis

### `setup_hooks.py`
**Purpose**: Interactive setup and configuration generator

**Features**:
- Makes scripts executable
- Generates Claude Code hook configurations
- Provides installation instructions
- Creates sample configuration files

## 🚀 Quick Start

### 1. Run Setup
```bash
cd hooks/
python setup_hooks.py
```

### 2. Choose Template
- **full_integration**: Complete memory system with search, storage, and analysis
- **memory_search_only**: Just context before operations (safest start)
- **error_prevention**: Focus on preventing repeated command failures
- **learning_focused**: Emphasize capturing and analyzing outcomes
- **conservative**: Only session-end analysis

### 3. Install Configuration
Copy the generated configuration to one of:
- `~/.claude/settings.json` (all projects)
- `.claude/settings.json` (this project only)
- `.claude/settings.local.json` (local development)

### 4. Test
Run any bash command or edit a file - you should see memory context appear automatically!

## 🔧 Configuration Examples

### Minimal Setup (Recommended Start)
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/mcp-mitm-mem0 && python hooks/memory_search.py"
          }
        ]
      }
    ]
  }
}
```

### Full Integration
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Edit|MultiEdit|Write|Read|Task",
        "hooks": [
          {
            "type": "command", 
            "command": "cd /path/to/mcp-mitm-mem0 && python hooks/memory_search.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash|Edit|MultiEdit|Write|Task",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/mcp-mitm-mem0 && python hooks/memory_store.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/mcp-mitm-mem0 && python hooks/memory_analyze.py"
          }
        ]
      }
    ]
  }
}
```

## 📊 What You'll See

### Before Operations (memory_search.py)
```
Found 3 relevant memories for Bash operation:

## Relevant Context from Memory

### 1. Memory from 2025-01-07T10:30:00Z
**Type**: error_resolution
Command `npm install` failed with EACCES error. Solution: use `sudo npm install` or fix npm permissions...

### 2. Memory from 2025-01-06T15:20:00Z
**Type**: command_execution  
Successfully installed dependencies using `npm ci` for faster, reliable installs...
```

### After Operations (memory_store.py)
```
Stored command_execution memory: mem_abc123
```

### Session End (memory_analyze.py)
```
🧠 Conversation analysis completed:

## Conversation Analysis Results

Analyzed 15 memories (8 recent, 7 semantically relevant)

### Frequent Questions
- User has asked 4 questions recently. Consider providing more proactive information.
- Examples: How to fix CORS?, What's the best testing approach?, Why is TypeScript complaining?

### Focus Area  
- Primary focus appears to be on coding (mentioned 6 times)
- Recommendation: Consider preparing more detailed resources on coding
```

## 🐛 Troubleshooting

### Hook Not Running
1. Check path in hook command matches your installation
2. Verify scripts are executable: `ls -la hooks/*.py`
3. Check Claude Code hook configuration: `/hooks` command

### No Memory Results
1. Verify MCP MITM Mem0 service is running
2. Check memory service has data: test MCP tools directly
3. Review hook execution logs: `~/.claude/hook_execution.log`

### Import Errors
1. Ensure you're in the project directory when hooks run
2. Verify mcp_mitm_mem0 package is installed: `uv run python -c "import mcp_mitm_mem0"`
3. Check Python path includes project directory

### Performance Issues
1. Reduce hook frequency by limiting `matcher` patterns
2. Check hook execution times in logs
3. Consider using only high-value hooks (Bash, Edit)

## 📝 Customization

### Target Specific Tools
```json
{
  "matcher": "Bash",  // Only bash commands
  "matcher": "Edit|MultiEdit|Write",  // File operations only  
  "matcher": "mcp__.*",  // All MCP tools
  "matcher": "",  // All tools
}
```

### Modify Search Behavior
Edit `memory_search.py`:
- Change search query generation logic
- Adjust memory result limits
- Customize error pattern detection

### Customize Storage
Edit `memory_store.py`:
- Modify memory type classification
- Change metadata generation
- Adjust storage criteria

### Tune Analysis
Edit `memory_analyze.py`:
- Change analysis trigger conditions
- Modify pattern recognition
- Adjust insight formatting

## 🔍 Debugging

### Execution Logs
```bash
tail -f ~/.claude/hook_execution.log
```

### Error Logs  
```bash
tail -f ~/.claude/hook_errors.log
```

### Test Hooks Manually
```bash
cd hooks/
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | python memory_search.py
```

### Check Hook Configuration
In Claude Code: `/hooks` command

## 🎯 Performance Tips

1. **Start Conservative**: Begin with `memory_search_only` or `conservative` templates
2. **Monitor Performance**: Check execution times in logs
3. **Selective Targeting**: Use specific matchers rather than all tools
4. **Gradual Expansion**: Add more hooks as you see value

## 🔮 Complete Integration

All 5 phases of the Claude Code hooks integration are now complete:

✅ **Phase 1**: Hook infrastructure with JSON I/O and configuration templates
✅ **Phase 2**: Session intelligence with Stop and Notification hooks
✅ **Phase 3**: Proactive memory integration with PreToolUse and PostToolUse hooks  
✅ **Phase 4**: Advanced pattern recognition with error prevention and project continuity
✅ **Phase 5**: Enhanced reflection with automatic triggers and memory curation

The complete system provides:
- **Deterministic memory access** - Claude always has relevant context
- **Automatic learning capture** - Solutions and patterns are never lost
- **Intelligent error prevention** - Past mistakes inform future actions
- **Seamless continuity** - Projects flow smoothly between sessions
- **Smart organization** - Memories are categorized and linked for optimal retrieval

Choose the configuration template that matches your needs:
- `conservative` - Start here for minimal impact
- `memory_search_only` - Just context provision
- `error_prevention` - Focus on avoiding repeated mistakes
- `project_continuity` - Maintain state across sessions
- `enhanced_reflection` - Automatic analysis and curation
- `ultimate_intelligence` - Everything enabled for maximum intelligence

The hooks ensure Claude never misses important context and continuously learns from every interaction!