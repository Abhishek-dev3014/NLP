import { Results } from '@/components/results';
export default async function ResultsPage({params}:{params:Promise<{id:string}>}){const {id}=await params;return <Results id={id}/>;}
