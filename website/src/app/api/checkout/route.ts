import { NextResponse } from 'next/server';
import Stripe from 'stripe';
import Razorpay from 'razorpay';

// Razorpay and Stripe are initialized inside the POST handler to avoid 
// module-level crashes when environment variables are missing.

export async function POST(req: Request) {
  console.log("Checkout API Hit!");
  try {
    const { planId, region, email } = await req.json();
    console.log("Request Data:", { planId, region, email });

    if (region === 'IN') {
      // --- RAZORPAY PATH (INDIA) ---
      
      if (!process.env.RAZORPAY_KEY_ID || !process.env.RAZORPAY_SECRET) {
        return NextResponse.json({ error: 'Razorpay keys are missing in .env.local' }, { status: 500 });
      }

      const razorpay = new Razorpay({
        key_id: process.env.RAZORPAY_KEY_ID,
        key_secret: process.env.RAZORPAY_SECRET,
      });

      const amounts: Record<string, number> = {
        '1-month': 50000,    // ₹500
        '3-month': 119900,   // ₹1,199
        'authority-pipeline': 360000,  // ₹3,600
        'sprint-one-dollar': 8000,     // ₹80 (~$1)
      };

      const amount = amounts[planId];
      if (!amount) return NextResponse.json({ error: 'Invalid plan' }, { status: 400 });

      const order = await razorpay.orders.create({
        amount: amount,
        currency: 'INR',
        receipt: `receipt_${Date.now()}`,
      });

      return NextResponse.json({ 
        gateway: 'razorpay',
        orderId: order.id,
        amount: order.amount,
        keyId: process.env.RAZORPAY_KEY_ID 
      });

    } else {
      // --- STRIPE PATH (INTERNATIONAL) ---
      
      if (!process.env.STRIPE_SECRET_KEY) {
        return NextResponse.json({ error: 'Stripe secret key is missing in .env.local' }, { status: 500 });
      }

      const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
        apiVersion: '2024-12-18.acacia' as any, // eslint-disable-line @typescript-eslint/no-explicit-any
      });
      
      const priceIds: Record<string, string | undefined> = {
        '1-month': process.env.STRIPE_PRICE_ROW_1M,
        '3-month': process.env.STRIPE_PRICE_ROW_3M,
        'authority-pipeline': process.env.STRIPE_PRICE_ROW_12M,
        'sprint-one-dollar': process.env.STRIPE_PRICE_SPRINT_1D,
      };

      const priceId = priceIds[planId];
      if (!priceId) return NextResponse.json({ error: 'Stripe Price ID is missing for this plan in .env.local' }, { status: 400 });

      const session = await stripe.checkout.sessions.create({
        payment_method_types: ['card'],
        line_items: [{ price: priceId, quantity: 1 }],
        mode: 'subscription',
        success_url: `${req.headers.get('origin')}/success?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${req.headers.get('origin')}/pricing`,
        customer_email: email,
      });

      return NextResponse.json({ 
        gateway: 'stripe',
        sessionId: session.id,
        url: session.url // Return the direct URL for checkout
      });
    }
  } catch (error: unknown) {
    console.error('Checkout API Error:', error);
    const errorMessage = error instanceof Error ? error.message : 'An internal server error occurred';
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
