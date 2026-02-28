"""Fine-tune Mistral 7B for compliance extraction using Unsloth + QLoRA.

Designed to run on BREV GPU instances under $100 total compute.
Logs everything to W&B Models.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def load_config(config_path: str = "training/config.yaml") -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_jsonl_dataset(path: str) -> list[dict]:
    samples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def format_for_sft(sample: dict) -> str:
    """Convert a chat-format sample to Mistral instruct format."""
    messages = sample.get("messages", [])
    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            parts.append(f"<s>[INST] {content}\n")
        elif role == "user":
            if parts:
                parts[-1] += f"{content} [/INST]"
            else:
                parts.append(f"<s>[INST] {content} [/INST]")
        elif role == "assistant":
            parts.append(f"{content}</s>")
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Mistral for Redline extraction")
    parser.add_argument("--config", default="training/config.yaml", help="Config YAML path")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without training")
    args = parser.parse_args()

    cfg = load_config(args.config)
    print(f"Config loaded: {cfg['model']['name']}")
    print(f"  LoRA rank: {cfg['lora']['rank']}, alpha: {cfg['lora']['alpha']}")
    print(f"  Epochs: {cfg['training']['num_train_epochs']}, LR: {cfg['training']['learning_rate']}")

    # Load data
    train_data = load_jsonl_dataset(cfg["data"]["train_path"])
    val_data = load_jsonl_dataset(cfg["data"]["val_path"])
    print(f"  Train: {len(train_data)} samples, Val: {len(val_data)} samples")

    if args.dry_run:
        print("\nDry run — config and data validated. Exiting.")
        formatted = format_for_sft(train_data[0])
        print(f"\nSample formatted input (first 300 chars):\n{formatted[:300]}...")
        return

    # GPU-dependent imports
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import Dataset
    import wandb

    # Initialize W&B
    wandb.init(
        project=cfg["wandb"]["project"],
        entity=cfg["wandb"].get("entity"),
        config=cfg,
        name=f"finetune-{cfg['model']['name'].split('/')[-1]}-r{cfg['lora']['rank']}",
    )

    # Load model with Unsloth
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=cfg["model"]["name"],
        max_seq_length=cfg["model"]["max_seq_length"],
        load_in_4bit=cfg["model"]["load_in_4bit"],
        dtype=cfg["model"]["dtype"],
    )

    # Apply LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r=cfg["lora"]["rank"],
        lora_alpha=cfg["lora"]["alpha"],
        lora_dropout=cfg["lora"]["dropout"],
        target_modules=cfg["lora"]["target_modules"],
        use_gradient_checkpointing="unsloth",
    )

    # Prepare datasets
    train_texts = [format_for_sft(s) for s in train_data]
    val_texts = [format_for_sft(s) for s in val_data]

    train_dataset = Dataset.from_dict({"text": train_texts})
    val_dataset = Dataset.from_dict({"text": val_texts})

    # Training arguments
    training_args = TrainingArguments(
        output_dir=cfg["training"]["output_dir"],
        num_train_epochs=cfg["training"]["num_train_epochs"],
        per_device_train_batch_size=cfg["training"]["per_device_train_batch_size"],
        gradient_accumulation_steps=cfg["training"]["gradient_accumulation_steps"],
        learning_rate=cfg["training"]["learning_rate"],
        lr_scheduler_type=cfg["training"]["lr_scheduler_type"],
        warmup_ratio=cfg["training"]["warmup_ratio"],
        weight_decay=cfg["training"]["weight_decay"],
        max_grad_norm=cfg["training"]["max_grad_norm"],
        fp16=cfg["training"]["fp16"],
        bf16=cfg["training"]["bf16"],
        logging_steps=cfg["training"]["logging_steps"],
        eval_strategy=cfg["training"]["eval_strategy"],
        eval_steps=cfg["training"]["eval_steps"],
        save_strategy=cfg["training"]["save_strategy"],
        save_steps=cfg["training"]["save_steps"],
        save_total_limit=cfg["training"]["save_total_limit"],
        seed=cfg["training"]["seed"],
        report_to="wandb",
        push_to_hub=cfg["hub"]["push_to_hub"],
        hub_model_id=cfg["hub"]["hub_model_id"],
        hub_strategy=cfg["hub"]["hub_strategy"],
    )

    # SFT Trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=cfg["model"]["max_seq_length"],
        packing=cfg["training"]["packing"],
    )

    # Train
    print("\nStarting training...")
    trainer.train()

    # Save LoRA adapter
    output_dir = Path(cfg["training"]["output_dir"])
    model.save_pretrained(output_dir / "final_adapter")
    tokenizer.save_pretrained(output_dir / "final_adapter")
    print(f"\nAdapter saved to {output_dir / 'final_adapter'}")

    # Log adapter as W&B artifact
    # SFTTrainer may have already closed the run, so re-init if needed
    if wandb.run is None:
        wandb.init(
            project=cfg["wandb"]["project"],
            entity=cfg["wandb"].get("entity"),
            name=f"finetune-{cfg['model']['name'].split('/')[-1]}-r{cfg['lora']['rank']}-artifact",
            config=cfg,
        )
    artifact = wandb.Artifact(
        name="redline-lora-adapter",
        type="model",
        description="LoRA adapter for compliance extraction",
    )
    artifact.add_dir(str(output_dir / "final_adapter"))
    wandb.log_artifact(artifact)
    wandb.finish()
    print("Training complete.")


if __name__ == "__main__":
    main()
