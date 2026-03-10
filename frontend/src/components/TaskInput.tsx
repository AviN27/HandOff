import { useState } from 'react';
import { Play, Link2, MessageSquare } from 'lucide-react';

interface TaskInputProps {
    onStart: (task: string, startUrl: string) => void;
    disabled: boolean;
}

export function TaskInput({ onStart, disabled }: TaskInputProps) {
    const [task, setTask] = useState('');
    const [url, setUrl] = useState('');

    const handleStart = () => {
        if (!task.trim()) return;
        onStart(task.trim(), url.trim());
    };

    const handleExampleClick = (exampleTask: string, exampleUrl: string) => {
        setTask(exampleTask);
        setUrl(exampleUrl);
    };

    return (
        <div className="glass-card" style={{ flex: '0 0 auto' }}>
            <div className="card-title">
                <MessageSquare size={20} className="text-accent-cyan" />
                New Mission
            </div>

            <div>
                <label className="input-label" htmlFor="url-input">Target URL (Optional)</label>
                <div style={{ position: 'relative' }}>
                    <Link2 size={18} style={{ position: 'absolute', top: '15px', left: '16px', color: 'var(--text-muted)' }} />
                    <input
                        id="url-input"
                        type="text"
                        className="input-field"
                        style={{ paddingLeft: '44px' }}
                        placeholder="e.g. google.com"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        disabled={disabled}
                    />
                </div>
            </div>

            <div>
                <label className="input-label" htmlFor="task-input">Agent Instructions</label>
                <textarea
                    id="task-input"
                    className="input-field"
                    placeholder="Describe perfectly what the agent should accomplish..."
                    value={task}
                    onChange={(e) => setTask(e.target.value)}
                    disabled={disabled}
                />
            </div>

            <button
                className="btn-primary"
                onClick={handleStart}
                disabled={disabled || !task.trim()}
            >
                <Play fill="currentColor" size={20} />
                Execute Mission
            </button>

            <div style={{ marginTop: '0.5rem' }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Quick Starts:</p>
                <div className="example-chips">
                    <span
                        className="chip"
                        onClick={() => handleExampleClick("Search for weather in Bangalore today", "https://google.com")}
                    >
                        Weather Search
                    </span>
                    <span
                        className="chip"
                        onClick={() => handleExampleClick("Find the latest tech news and summarize headlines", "https://news.ycombinator.com")}
                    >
                        Hacker News Reader
                    </span>
                    <span
                        className="chip"
                        onClick={() => handleExampleClick("Look up flights from SFO to JFK for next Friday", "https://flights.google.com")}
                    >
                        Book Flights
                    </span>
                </div>
            </div>
        </div>
    );
}
