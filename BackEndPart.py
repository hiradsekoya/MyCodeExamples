from flask import Flask, request, jsonify, render_template
import os
import torch
import warnings
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig

# Suppress warnings
warnings.filterwarnings("ignore", message="get_max_cache() is deprecated")
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = Flask(__name__)

# Detect TPU availability
def is_tpu_available():
    try:
        import torch_xla.core.xla_model as xm
        return True
    except ImportError:
        return False

# Set device (TPU, GPU, or CPU)
if is_tpu_available():
    import torch_xla.core.xla_model as xm
    device = xm.xla_device()
    print("Using device: TPU")
elif torch.cuda.is_available():
    device = torch.device("cuda")
    print("Using device: GPU")
else:
    device = torch.device("cpu")
    print("Using device: CPU")

# Set quantization engine for CPU
if device == torch.device("cpu"):
    torch.backends.quantized.engine = "qnnpack"
    print("Quantization engine set to:", torch.backends.quantized.engine)

# Cache for loaded models and tokenizers
model_cache = {}

def load_model_and_tokenizer(model_name):
    if model_name in model_cache:
        return model_cache[model_name]

    print(f"\nLoading model: {model_name}...")
    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, config=config, trust_remote_code=True)

    model.to(device)

    if device == torch.device("cpu"):
        print("Applying dynamic quantization...")
        model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_cache[model_name] = (model, tokenizer)
    return model, tokenizer

# Generate text from prompt with an optional programming language prefix.
def generate_text(model_name, prompt, programming_language=None):
    try:
        model, tokenizer = load_model_and_tokenizer(model_name)
        print(f"Generating text with model: {model_name}")

        # Prepend a note if a programming language is selected.
        if programming_language:
            prompt = f"// Code in {programming_language}\n" + prompt

        inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        outputs = model.generate(
            inputs["input_ids"],
            attention_mask=inputs.get("attention_mask", None),
            max_length=1000,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=False,
            temperature=0.7,
            top_p=0.9,
            num_return_sequences=1
        )
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return generated_text

    except Exception as e:
        print(f"Error during generation with model {model_name}: {str(e)}")
        return None

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    prompt = data.get('prompt', '')
    single_model = data.get('model_name', '')
    multi_models = data.get('multi_model_names', [])
    programming_language = data.get('programming_language', '')

    if not prompt:
        return jsonify({'error': 'Prompt is required.'}), 400

    # If multiple models were selected, generate a file with all outputs.
    if multi_models and len(multi_models) > 0:
        file_contents = ""
        for model in multi_models:
            generated_text = generate_text(model, prompt, programming_language)
            if generated_text:
                file_contents += f"Output from model {model}:\n{generated_text}\n\n"
            else:
                file_contents += f"Output from model {model}:\n[Error or no output generated]\n\n"
        return jsonify({'file_text': file_contents})
    else:
        if not single_model:
            return jsonify({'error': 'Model name is required for single model generation.'}), 400
        generated_text = generate_text(single_model, prompt, programming_language)
        if generated_text:
            return jsonify({'generated_text': generated_text})
        else:
            return jsonify({'error': 'Text generation failed.'}), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
