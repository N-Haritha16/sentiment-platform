export async function sendText(text) {
  try {
    const response = await fetch("http://localhost:8000/ingest", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      throw new Error("Failed to send text");
    }

    return await response.json();
  } catch (error) {
    console.error("Error sending text:", error);
    throw error;
  }
}
