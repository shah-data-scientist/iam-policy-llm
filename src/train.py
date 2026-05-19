"""
CLI training script — mirrors notebook 02_finetune.ipynb.
Run on Google Colab or any machine with a CUDA GPU.

Usage:
    python src/train.py --data data/processed/train.jsonl --output outputs/
"""

import argparse
from datasets import Dataset
from data_utils import load_jsonl, format_prompt


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/processed/train.jsonl")
    parser.add_argument("--output", default="outputs/")
    parser.add_argument("--model", default="unsloth/llama-3.2-3b-instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--rank", type=int, default=16)
    return parser.parse_args()


def train(args):
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=2048,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.rank,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_alpha=args.rank,
        lora_dropout=0.05,
        bias="none",
    )

    raw = load_jsonl(args.data)
    dataset = Dataset.from_list([{"text": format_prompt(ex)} for ex in raw])

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            num_train_epochs=args.epochs,
            learning_rate=2e-4,
            fp16=True,
            output_dir=args.output,
            logging_steps=10,
            save_steps=100,
        ),
    )

    trainer.train()
    model.save_pretrained("iam-policy-adapter")
    tokenizer.save_pretrained("iam-policy-adapter")
    print("Adapter saved to iam-policy-adapter/")


if __name__ == "__main__":
    train(get_args())
