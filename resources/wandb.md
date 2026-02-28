<aside>
💛

**Welcome, hackers!** This is your single source of truth for everything Weights & Biases at the [Mistral Worldwide Hackathon](https://worldwide-hackathon.mistral.ai/) — February 28 – March 1, 2026. Whether you're fine-tuning Mistral models, building agents, or pushing on-device AI, W&B has you covered. Jump to [Quickstart Guide](https://www.notion.so/W-B-at-Mistral-Worldwide-Hackathon-2026-311e2f5c7ef3806c8b01fc18b21757c4?pvs=21) to see how best to get started. 

</aside>

---

## 🏆 W&B Fine-Tuning Track

### *Push the Limits — Fine-Tune Mistral Models to Master Any Task*

W&B is the **Global Track Sponsor** and we're hosting the **Fine-Tuning Track**. This track is for technically strong builders who want to fine-tune **Ministral, Mistral Small, Mistral Medium, Codestral, or other Mistral models** on a specific task of their choosing.

You can fine-tune however you like:

- **On your own** using tools like [Unsloth](https://github.com/unslothai/unsloth), Hugging Face Transformers, or any other framework
- **Using Mistral's fine-tuning APIs** — see the [Mistral Fine-Tuning Docs](https://docs.mistral.ai/capabilities/finetuning/)
- **Using W&B Training** — our serverless SFT and RL post-training service powered by OpenPipe's ART framework. Supports GRPO and SFT out of the box. See [W&B Training Docs](https://docs.wandb.ai/training) and the [ART Quickstart](https://art.openpipe.ai/getting-started/quick-start)

### Judging Criteria — Fine-Tuning Track

| **Criteria** | **Description** | **Weight** |
| --- | --- | --- |
| **Technical Quality** | Task-fit - does it make sense to fine-tune (show superior performance to prompt engineering only)? 

Quality and complexity - how good is the fine-tuning? Incl. workflow completeness and complexity (data preparation, model selection, evals, optimization), benchmark maturity and optimization improvements and viability of final model for task. | ⭐⭐⭐⭐ |
| **E2E Points (Models + Weave)** | Extra points if you use W&B Models *and* Weave together — e.g. fine-tune a model and then trace & evaluate it as part of an agent pipeline.  | ⭐⭐ |
| **Experiment Tracking and Artifacts Logging (W&B Models)** | Loss plots and key metrics are tracked in W&B Models. We want to see your training runs! We also expect you to save your model as an Artifact and log to HF for us to validate (e.g. the LoRA adaptors).  | ⭐ |
| **Tracing and Evaluation (W&B Weave)** | Likely you’ll integrate the model into an agent that needs to be evaluated (and maybe traced) - show us the traces and best evaluation in W&B Weave! | ⭐ |
| **W&B Report** | A W&B Report summarizing your key findings, training curves, and results. *Tip: use the W&B MCP to help generate your report! 📊 Plots will be shipped as an MCP tool update soon — factor this into the report criteria.* | ⭐⭐ |

---

## 🤖 Supporting the Agents (Mistral) & On-Device (NVIDIA) Tracks

W&B also supports the other two tracks at the hackathon:

### Mistral Agents Track

Build agents powered by Mistral models. **W&B Weave** is your best friend here — trace every LLM call, tool use, and agent decision. Our **new [audio evals and monitors](https://docs.wandb.ai/weave/guides/evaluation/monitors#set-up-monitors)** are especially relevant if you're building with [**Voxtral**](https://mistral.ai/news/voxtral) (Mistral's voice model). Use Weave to evaluate and monitor your agent's audio interactions in production.

### NVIDIA On-Device Track

Deploy Mistral models on-device. Use [**W&B Models**](https://docs.wandb.ai/models) to track your quantization experiments and optimizations, and [**W&B Weave**](https://docs.wandb.ai/weave) to trace and evaluate on-device inference quality.

> **For both tracks:** Log your experiments in W&B and use Weave for tracing — this will help you stand out in judging!
> 

---

## 🔄 Mini Challenge: Best Self-Improvement Workflow

<aside>
🎯

**The more details the better!** Fill out the [Self-Improvement Challenge Feedback Form](https://forms.gle/bd3bo4BMFBpeWuyh6) to provide additional context on your workflow.

</aside>

### *$500 CoreWeave Inference Credits + Mac Mini*

Show us the **best self-improvement workflow** built on the [**W&B MCP Server and Skills**](https://github.com/wandb/wandb-mcp-server). Demonstrate that your coding agent (Cursor, Claude Code, Gemini CLI, etc.) can automatically evaluate, optimize, and improve your AI application using W&B tools.

### What we're looking for:

- **Automated evals creation** — your agent uses W&B MCP tools to create and run evaluations
- **Optimization loop** — the agent inspects results and iterates to improve performance
- **Smart delegation** — creative use of W&B tools and skills to let the model drive the improvement cycle

### Judging Criteria — Mini Challenge

| **Criteria** | **Description** | **Required?** |
| --- | --- | --- |
| **Proven Improvement** | Show a measurable metric increase, a video walkthrough, or a detailed text description of the automation achieved by the (coding) agent using W&B MCP or skills | ✅ Required |
| **Generated Skills Submitted** | Submit the skills/prompts/configs your agent generated during the workflow | ✅ Required |
| **Creativity** | How creative and novel is the automation approach? | Judged |
| **Completeness** | Is the workflow end-to-end? Does it cover eval → analysis → improvement? | Judged |

---

## 🚀 Quickstart Guide

<aside>
🔑

**First things first:** Create your free W&B account at [wandb.ai/authorize](http://wandb.ai/authorize) and grab your API key from [wandb.ai/settings](http://wandb.ai/settings).

</aside>

### 1. W&B MCP Server *(good place to start!)*

The [W&B MCP and skills](https://github.com/wandb/wandb-mcp-server) is the fastest way to supercharge your hackathon workflow. It lets your coding agent directly interact with W&B — analyze runs, debug traces, create reports, and start an automated improvement loop.

| **Analyze Experiments** | **Debug Traces** | **Create Reports** | **Get Help** |
| --- | --- | --- | --- |
| "Show me my top 5 runs by accuracy" | "How did latency evolve over the last 24 hours?" | "Generate a report comparing my fine-tuning runs" | "How do I create a leaderboard in Weave?" |
- **Add to Cursor** (click or paste the config below)
    
    ```json
    "wandb": {
      "transport": "http",
      "url": "https://mcp.withwandb.com/mcp",
      "headers": {
        "Authorization": "Bearer <your-wandb-api-key>",
        "Accept": "application/json, text/event-stream"
      }
    }
    ```
    
- **Claude Code**
    
    ```bash
    claude mcp add --transport http wandb https://mcp.withwandb.com/mcp --header "Authorization: Bearer <your-api-key>"
    ```
    
- **Gemini CLI**
    
    ```bash
    export WANDB_API_KEY="your-api-key-here"
    gemini extensions install https://github.com/wandb/wandb-mcp-server
    ```
    
- **OpenAI Codex**
    
    ```bash
    export WANDB_API_KEY=<your-api-key>
    codex mcp add wandb --url https://mcp.withwandb.com/mcp --bearer-token-env-var WANDB_API_KEY
    ```
    
- **VSCode**
    
    In `.vscode/mcp.json`:
    
    ```json
    {
      "servers": {
        "wandb": {
          "type": "http",
          "url": "https://mcp.withwandb.com/mcp",
          "headers": {
            "Authorization": "Bearer YOUR_WANDB_API_KEY"
          }
        }
      }
    }
    ```
    
- **OpenAI Responses API** (use Weave as your self-improvement backbone)
    
    ```python
    from openai import OpenAI
    import os
    
    client = OpenAI()
    
    resp = client.responses.create(
        model="gpt-4o",
        tools=[{
            "type": "mcp",
            "server_url": "https://mcp.withwandb.com/mcp",
            "authorization": os.getenv('WANDB_API_KEY'),
        }],
        input="How many traces are in my project?"
    )
    print(resp.output_text)
    ```
    

👉 See all connectors and details on the [W&B MCP GitHub](https://github.com/wandb/wandb-mcp-server)

### 2. W&B Weave — Trace & Evaluate Your Agents

Weave is W&B's observability and evaluation platform for LLM apps. Add tracing to your Mistral-powered agent in just a few lines.

```python
import weave
import os
from mistralai import Mistral

# Initialize Weave — all Mistral calls are now traced!
weave.init("mistral-hackathon")

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

response = client.chat.complete(
    model="mistral-small-latest",
    messages=[{"role": "user", "content": "Hello Mistral!"}]
)
```

**Key docs:**

- [W&B Weave Quickstart](https://docs.wandb.ai/weave)
- [Weave × Mistral Integration](https://docs.wandb.ai/weave/guides/integrations/mistral)
- [Evaluation Guide](https://docs.wandb.ai/weave/guides/evaluation/scorers)

### 3. W&B Models — Track Experiments & Fine-Tuning

W&B Models is the system of record for tracking training runs, comparing experiments, and managing model artifacts.

```python
import wandb

wandb.init(project="mistral-hackathon")

# Log metrics during training
wandb.log({"loss": 0.42, "eval_accuracy": 0.87})

# Log your adapter as an artifact
artifact = wandb.Artifact("mistral-lora-adapter", type="model")
artifact.add_dir("./adapter_weights")
wandb.log_artifact(artifact)
```

**Key docs:**

- [W&B Models Quickstart](https://docs.wandb.ai/models/quickstart)
- [W&B Reports](https://docs.wandb.ai/models/app/features/panels)
- [Mistral + W&B Fine-Tuning Cookbook](https://docs.mistral.ai/cookbooks/third_party-wandb-02_finetune_and_eval)

### 4. Mistral Fine-Tuning Resources

- [Mistral Fine-Tuning API Docs](https://docs.mistral.ai/capabilities/finetuning/)
- [Mistral + W&B: Fine-tune an LLM Judge (Cookbook)](https://docs.mistral.ai/cookbooks/third_party-wandb-02_finetune_and_eval)
- [Unsloth — Fast Fine-Tuning](https://github.com/unslothai/unsloth)

---

## 👋 On-Site Contacts

Find the W&B team at your location — we're here to help you build, debug, and win!

| **City** | **W&B Contacts** |
| --- | --- |
| 🇺🇸 **San Francisco** | Alex Volkov, Anu Vatsa, Nicolas Remerscheid, Julia Rose |
| 🇬🇧 **London** | Junaid Butt |
| 🇫🇷 **Paris** | Sarah Carthy, Salomé Froment |
| 🇺🇸 **New York City** | Anish Shah, Uma Krishnaswamy |
| 🇯🇵 **Tokyo** | Kei Kamata, Yuya Yamamoto |

> Don't hesitate to reach out — we're here to help you debug, brainstorm, and get the most out of W&B! Look for people in **W&B gear** 💛
> 

---

<aside>
🔗

**Useful Links**

- [Self-Improvement Challenge Feedback Form](https://forms.gle/bd3bo4BMFBpeWuyh6) - Mini Challenge
- [W&B MCP Server (GitHub)](https://github.com/wandb/wandb-mcp-server)
- [W&B Weave Docs](https://docs.wandb.ai/weave) (incl. [audio/image online monitoring](https://docs.wandb.ai/weave/guides/evaluation/monitors#how-to-create-a-monitor-in-weave))
- [W&B Models Docs](https://docs.wandb.ai/models)
- [W&B Training Docs](https://docs.wandb.ai/training)
- [Mistral Fine-Tuning Docs](https://docs.mistral.ai/capabilities/finetuning/)
- Example projects
    - [Hiring Agent: E2E AI Evaluation for Fair & Auditable Hiring Decisions](https://wandb.ai/wandb-smle/hiring-agent-demo-public/reports/Hiring-Agent-E2E-AI-Evaluation-for-Fair-Auditable-Hiring-Decisions--VmlldzoxMjI0MjI0Mw)
    - [Unlocking GPU power: Teaching AI to write Triton kernels](https://wandb.ai/grpo-cuda/axolotl-grpo/reports/Unlocking-GPU-power-Teaching-AI-to-write-Triton-kernels--VmlldzoxMjQ1MzEyOQ)
</aside>
