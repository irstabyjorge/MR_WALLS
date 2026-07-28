import { Ollama } from 'ollama'

const host = process.env.OLLAMA_HOST ?? 'http://127.0.0.1:11434'
const model = process.env.JEFEAGUILA_MODEL ?? 'llama3.2:3b'
const client = new Ollama({ host })

const response = await client.chat({
  model,
  messages: [
    {
      role: 'system',
      content:
        'You are JEFEAGUILA, a local, defensive, evidence-first assistant. ' +
        'Distinguish facts, technical data, user statements, inferences, ' +
        'hypotheses, contradictions, and unverified claims.',
    },
    { role: 'user', content: 'Reply: JEFEAGUILA JavaScript client works.' },
  ],
})

console.log(response.message.content)
