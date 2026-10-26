import Link from 'next/link';
import { Button } from '@/components/ui/button';
export default function NotFound(){return <div className="empty-state"><p className="eyebrow">404 · ANOTHER DIRECTION</p><h1 className="text-3xl mb-4">This page couldn’t be found.</h1><p>Return to the analyzer to keep exploring.</p><Button asChild><Link href="/analyze">Open the analyzer</Link></Button></div>;}
