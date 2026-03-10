import { useEffect, useRef } from 'react';
import { AgentAction } from '../lib/types';
import { ListTree, CheckCircle2, XCircle } from 'lucide-react';

interface ActionFeedProps {
    actions: { step: number; data: AgentAction }[];
}

export function ActionFeed({ actions }: ActionFeedProps) {
    const feedRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (feedRef.current) {
            feedRef.current.scrollTop = feedRef.current.scrollHeight;
        }
    }, [actions.length]);

    return (
        <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div className="card-title">
                <ListTree size={20} style={{ color: 'var(--accent-blue)' }} />
                Action Telemetry
            </div>

            <div className="scroll-area" ref={feedRef} style={{ marginTop: '0.5rem' }}>
                {actions.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', padding: '2rem 1rem' }}>
                        No actions executed yet.
                    </div>
                ) : (
                    actions.map((item, index) => (
                        <div key={index} className="action-row">
                            <div className="action-step-badge">#{item.step}</div>
                            <div className="action-details" style={{ flex: 1 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <h4>{item.data.action}</h4>
                                    {item.data.success ? (
                                        <CheckCircle2 size={16} color="var(--accent-green)" />
                                    ) : (
                                        <XCircle size={16} color="var(--accent-red)" />
                                    )}
                                </div>
                                <p>{item.data.detail || JSON.stringify(item.data.args)}</p>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
