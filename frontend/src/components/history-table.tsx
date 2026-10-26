'use client';
import Link from 'next/link';
import { ArrowUpRight, Trash2 } from 'lucide-react';
import type { Analysis } from '@/lib/types';
import { formatDate, percent } from '@/lib/utils';
import { AssessmentBadge } from './common';
import { ConfirmDialog } from './ui/dialog';
export function HistoryTable({items,onDelete,pending=false}:{items:Analysis[];onDelete?:(id:string)=>void;pending?:boolean}){return <div className="table-scroll"><table><thead><tr><th>Article / headline</th><th>Analyzed</th><th>NLP assessment</th><th>Model confidence</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{items.map(a=><tr key={a.id}><td className="headline-cell"><Link href={`/results/${a.id}`} title={a.headline}>{a.headline}</Link><small>{a.insights.word_count} words · {a.input_type.toUpperCase()}</small></td><td className="whitespace-nowrap">{formatDate(a.created_at)}</td><td><AssessmentBadge label={a.prediction.label}/></td><td className="font-mono">{percent(a.prediction.confidence)}</td><td><div className="table-actions"><Link href={`/results/${a.id}`} className="table-action" aria-label={`Open ${a.headline}`}><ArrowUpRight size={13}/></Link>{onDelete&&<ConfirmDialog title="Delete this analysis?" description="This permanently removes the article, its insights, claims, and report from your history." onConfirm={()=>onDelete(a.id)} pending={pending} trigger={<button className="table-action" disabled={pending} aria-label={`Delete ${a.headline}`}><Trash2 size={12}/></button>}/>}</div></td></tr>)}</tbody></table></div>;}
