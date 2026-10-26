'use client';
import { ErrorState } from '@/components/common';
export default function ErrorPage({reset}:{reset:()=>void}){return <div className="page-article"><ErrorState message="This page could not be displayed. Reload it or return to your history to recover a saved report." retry={reset}/></div>;}
