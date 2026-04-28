import { NextResponse } from 'next/server';
import Razorpay from 'razorpay';

// Razorpay is initialized inside the POST handler to avoid
// module-level crashes when environment variables are missing.

export async function POST(req: Request) {
  console.log("Checkout API Hit!");
  try {
    const { planId, region, email } = await req.json();
    console.log("Request Data:", { planId, region, email });

    // --- RAZORPAY PATH (ALL REGIONS) ---
    const keyId = process.env.RAZORPAY_KEY_ID;
    const keySecret = process.env.RAZORPAY_KEY_SECRET || process.env.RAZORPAY_SECRET;
    if (!keyId || !keySecret) {
      return NextResponse.json({ error: 'Razorpay keys are missing in .env.local' }, { status: 500 });
    }

    const razorpay = new Razorpay({
      key_id: keyId,
      key_secret: keySecret,
    });

    const isIndia = region === 'IN';
    const planMap = isIndia
      ? {
          starter: { amount: 59900, currency: 'INR' },
          '1-month': { amount: 59900, currency: 'INR' },
          creator: { amount: 129900, currency: 'INR' },
          '3-month': { amount: 129900, currency: 'INR' },
        }
      : {
          starter: { amount: 1900, currency: 'USD' },
          '1-month': { amount: 1900, currency: 'USD' },
          creator: { amount: 2900, currency: 'USD' },
          '3-month': { amount: 2900, currency: 'USD' },
        };

    const selected = planMap[planId as keyof typeof planMap];
    if (!selected) {
      return NextResponse.json({ error: 'Invalid plan' }, { status: 400 });
    }

    const order = await razorpay.orders.create({
      amount: selected.amount,
      currency: selected.currency,
      receipt: `receipt_${Date.now()}`,
      notes: {
        region,
        planId,
        email: email || '',
      },
    });

    return NextResponse.json({
      gateway: 'razorpay',
      orderId: order.id,
      amount: order.amount,
      currency: order.currency,
      keyId,
    });
  } catch (error: unknown) {
    console.error('Checkout API Error:', error);
    const errorMessage = error instanceof Error ? error.message : 'An internal server error occurred';
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
