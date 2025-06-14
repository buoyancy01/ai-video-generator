import React, { useState } from 'react';
import axios from 'axios';
// Removed: import './index.css'; as it's not being used and isn't part of your current setup

export default function App() {
  const [file, setFile] = useState(null);
  const [script, setScript] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(""); // State to store error messages

  // --- IMPORTANT: This will be updated with your actual Render backend URL after deployment ---
  // Temporarily, you can leave it as "YOUR_RENDER_BACKEND_URL" for the initial GitHub push.
  // You will update this EXACT string with the URL provided by Render AFTER your backend deploys.
  const BACKEND_URL = "https://ai-video-generator-wrfb.onrender.com"; // Example: "https://ai-video-generator-backend.onrender.com"

  const handleSubmit = async (e) => {
    e.preventDefault();
    setVideoUrl(""); // Clear previous video
    setError(""); // Clear previous errors
    setLoading(true);

    if (!file) {
      setError("Please select an image file.");
      setLoading(false);
      return;
    }
    if (!script.trim()) {
      setError("Please enter a script.");
      setLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("script", script);

    try {
      console.log(`Sending request to backend: ${BACKEND_URL}/generate`);
      const res = await axios.post(`${BACKEND_URL}/generate`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      console.log("Backend response:", res.data);
      if (res.data && res.data.video_url) {
        setVideoUrl(res.data.video_url);
      } else {
        setError("Video URL missing from backend response.");
      }
    } catch (err) {
      console.error("Error generating video:", err);
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        setError(`Backend error: ${err.response.status} - ${err.response.data.detail || err.response.statusText}`);
      } else if (err.request) {
        // The request was made but no response was received
        setError("Network error: Could not connect to the backend server. Is it running?");
      } else {
        // Something happened in setting up the request that triggered an Error
        setError(`An unexpected error occurred: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '32px', fontFamily: 'sans-serif', maxWidth: '640px', margin: 'auto', backgroundColor: '#fff', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', borderRadius: '8px', marginTop: '32px' }}>
      <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '16px', textAlign: 'center', color: '#333' }}>AI Product Video Generator</h1>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <label htmlFor="file-upload" style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#333', marginBottom: '8px' }}>Upload Product Image:</label>
          <input
            id="file-upload"
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
            required
            style={{ display: 'block', width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>
        <div>
          <label htmlFor="script-input" style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#333', marginBottom: '8px' }}>Enter Video Script:</label>
          <textarea
            id="script-input"
            placeholder="e.g., 'Introducing our new eco-friendly water bottle, designed for active lifestyles...'"
            value={script}
            onChange={(e) => setScript(e.target.value)}
            required
            rows="5"
            style={{ border: '1px solid #ccc', padding: '12px', borderRadius: '6px', width: '100%', boxSizing: 'border-box', resize: 'vertical', fontSize: '1rem' }}
          />
        </div>
        <button
          type="submit"
          style={{ backgroundColor: loading ? '#9b9b9b' : '#3b82f6', color: '#fff', fontWeight: 'bold', padding: '12px 20px', borderRadius: '6px', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', transition: 'background-color 0.2s ease-in-out' }}
          disabled={loading}
        >
          {loading ? "Generating Video..." : "Generate Video"}
        </button>
      </form>

      {error && (
        <p style={{ marginTop: '24px', padding: '12px', backgroundColor: '#fee2e2', color: '#dc2626', border: '1px solid #ef4444', borderRadius: '6px', textAlign: 'center' }}>
          Error: {error}
        </p>
      )}

      {loading && <p style={{ marginTop: '24px', textAlign: 'center', color: '#666' }}>Please wait, video generation can take up to a minute...</p>}

      {videoUrl && (
        <div style={{ marginTop: '24px' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#333', marginBottom: '12px', textAlign: 'center' }}>Generated Video:</h2>
          <video
            style={{ width: '100%', height: 'auto', borderRadius: '6px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', backgroundColor: '#000' }}
            controls
            src={videoUrl}
            onLoadStart={() => console.log("Video loading started...")}
            onLoadedData={() => console.log("Video data loaded.")}
            onError={(e) => console.error("Video playback error:", e)}
          >
            Your browser does not support the video tag.
          </video>
          <p style={{ textAlign: 'center', fontSize: '0.875rem', color: '#888', marginTop: '8px' }}>If video does not play, try copying the URL and pasting in a new tab.</p>
        </div>
      )}
    </div>
  );
}